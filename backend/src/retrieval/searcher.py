"""
混合检索 + PageIndex Tree + Rerank 完整流程
从 settings 读取 Qdrant / MongoDB 配置，而非硬编码。
"""

import logging
import os
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class HybridSearcher:
    """混合检索器 + PageIndex Tree + Rerank"""

    def __init__(self, settings: Any):
        from qdrant_client import QdrantClient

        self.client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )
        self.collection_name = settings.qdrant_collection
        self.mongodb_uri = settings.mongodb_uri
        self.mongodb_database = settings.mongodb_database

        logger.info(
            "初始化 HybridSearcher: qdrant=%s:%d, collection=%s",
            settings.qdrant_host,
            settings.qdrant_port,
            self.collection_name,
        )

        # 加载 Tree 结构（用于获取标题/摘要）
        self.trees = self._load_trees()

        # 按需加载章节内容
        self.corpus_cache: Dict[str, str] = {}

        # Reranker 延迟初始化
        self.reranker = None

        logger.info("HybridSearcher 初始化完成: %d 本小说", len(self.trees))

    def _load_corpus_item(self, novel_id: str, node_id: str) -> str:
        """按需从 OSS 加载单个章节内容"""
        cache_key = f"{novel_id}_{node_id}"

        if cache_key in self.corpus_cache:
            return self.corpus_cache[cache_key]

        from .oss_manager import oss_manager

        oss_path = f"novels/structured/{novel_id}/nodes/{node_id}.txt"

        try:
            content = oss_manager.download_content(oss_path)
            self.corpus_cache[cache_key] = content
            logger.debug("[Corpus] 加载: %s", oss_path)
            return content
        except Exception as e:
            logger.warning("[Corpus] 加载失败: %s - %s", oss_path, e)
            return ""

    def _load_trees(self) -> Dict[str, Dict]:
        """从 MongoDB 加载 PageIndex Tree 结构"""
        from pymongo import MongoClient

        logger.info("[Tree] 开始加载 PageIndex Tree 结构...")

        # 从 Qdrant 获取所有已入库的小说
        all_novel_ids = self._get_all_novel_ids()
        logger.info("[Tree] 发现 %d 本小说在 Qdrant 中", len(all_novel_ids))

        client = MongoClient(self.mongodb_uri)
        db = client[self.mongodb_database]

        trees = {}

        for novel_info in all_novel_ids:
            novel_id = novel_info["novel_id"]
            tree = db.trees.find_one({"novel_id": novel_id})
            if tree:
                novel_name = tree.get("novel_name", novel_id)
                ts = tree.get("tree_structure", {})
                structure = ts.get("structure", [])

                node_map = {}
                for node in structure:
                    nid = node.get("node_id", "")
                    node_map[nid] = {
                        "title": node.get("title", ""),
                        "summary": node.get("summary", ""),
                        "text": node.get("text", ""),
                        "level": node.get("level", 1),
                        "start_index": node.get("start_index", 0),
                        "end_index": node.get("end_index", 0),
                    }

                trees[novel_name] = {
                    "novel_id": novel_id,
                    "node_map": node_map,
                }
                logger.info("[Tree] 加载 %s: %d 个节点", novel_name, len(node_map))
            else:
                logger.warning("[Tree] 未找到 tree: %s", novel_id)

        logger.info("[Tree] 总共加载 %d 本小说的 Tree 结构", len(trees))
        return trees

    def _get_all_novel_ids(self) -> List[Dict]:
        """从 Qdrant 获取所有已入库的小说"""
        result, _ = self.client.scroll(
            collection_name=self.collection_name,
            limit=10000,
            with_payload=True,
            with_vectors=False,
        )

        novel_infos: Dict[str, Dict] = {}
        for point in result:
            novel_id = point.payload.get("novel_id")
            if novel_id and novel_id not in novel_infos:
                novel_infos[novel_id] = {
                    "novel_id": novel_id,
                    "prefix": f"novels/structured/{novel_id}/nodes/",
                }

        return list(novel_infos.values())

    def _get_tree_node(self, novel_name: str, node_id: str) -> Optional[Dict]:
        """从 PageIndex Tree 中获取节点信息"""
        if novel_name not in self.trees:
            logger.warning("[Tree] 未找到小说: %s", novel_name)
            return None

        node = self.trees[novel_name]["node_map"].get(node_id)
        if node:
            logger.debug(
                "[Tree] 找到节点: %s/%s -> %s",
                novel_name, node_id, node.get("title"),
            )
        else:
            logger.warning("[Tree] 未找到节点: %s/%s", novel_name, node_id)
        return node

    def _init_reranker(self):
        """初始化 Reranker"""
        if self.reranker is not None:
            return

        logger.info("[Rerank] 尝试初始化 Reranker...")

        proxy = os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY")
        if proxy:
            os.environ["http_proxy"] = proxy
            os.environ["https_proxy"] = proxy
            logger.info("[Rerank] 使用代理: %s", proxy)

        try:
            from FlagEmbedding import FlagReranker

            self.reranker = FlagReranker("BAAI/bge-reranker-base", use_fp16=True)
            logger.info("[Rerank] Reranker 初始化成功!")
        except Exception as e:
            logger.warning("[Rerank] Reranker 初始化失败: %s", e)
            self.reranker = False

    def hybrid_search_native(self, query: str, top_k: int = 5):
        """Qdrant 原生 Hybrid Search (Dense + RRF)"""
        from qdrant_client import models
        from .embedding_client import embedding_client

        logger.info(
            "[Qdrant Hybrid] 开始原生混合检索, query='%s', top_k=%d",
            query, top_k,
        )

        dense_vector = embedding_client.embed(query)
        if not dense_vector:
            logger.error("[Qdrant Hybrid] 生成向量失败!")
            return []

        results = self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                models.Prefetch(
                    query=dense_vector,
                    using="dense",
                    limit=top_k * 2,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=top_k,
            with_payload=True,
        )

        hybrid_results = []
        logger.info(
            "[Qdrant Hybrid] 检索到 %d 个结果", len(results.points),
        )
        for r in results.points:
            node_id = r.payload["node_id"]
            novel_name = r.payload.get("novel_name", "")
            novel_id = r.payload.get("novel_id", "")
            score = r.score
            hybrid_results.append((node_id, score, novel_name, novel_id))
            logger.info(
                "  - %s/%s: score=%.6f", novel_name, node_id, score,
            )

        return hybrid_results

    def _rerank(
        self, query: str, results: List[Dict], *, score_gap: float = 0
    ) -> List[Dict]:
        """使用 Reranker 重新排序，并按 score_gap 裁剪离群结果。

        Args:
            score_gap: 与最佳结果的分数差距阈值。>0 时启用裁剪，
                       差距超过此值的结果被移除。0 表示不裁剪。
        """
        self._init_reranker()

        if not self.reranker:
            logger.warning("[Rerank] Reranker 不可用，跳过重排序")
            return results

        logger.info("[Rerank] 开始重排序, %d 个候选", len(results))

        pairs = []
        for r in results:
            text = r.get("tree_node", {}).get("summary", "")[:500]
            if not text:
                text = r.get("content", "")[:500]
            pairs.append([query, text])

        try:
            scores = self.reranker.compute_score(pairs)

            for i, r in enumerate(results):
                r["rerank_score"] = scores[i] if i < len(scores) else 0

            results = sorted(results, key=lambda x: x["rerank_score"], reverse=True)

            logger.info("[Rerank] 重排序完成:")
            for i, r in enumerate(results[:5], 1):
                logger.info(
                    "  %d. %s/%s: rerank=%.6f",
                    i, r["novel_name"], r["node_id"], r["rerank_score"],
                )

            # Gap 过滤：裁剪与最佳结果差距过大的离群结果
            if score_gap > 0 and results:
                best_score = results[0]["rerank_score"]
                before_count = len(results)
                results = [
                    r for r in results
                    if best_score - r["rerank_score"] <= score_gap
                ]
                if len(results) < before_count:
                    logger.info(
                        "[Rerank] Gap 过滤 (threshold=%.1f): %d -> %d",
                        score_gap, before_count, len(results),
                    )

        except Exception as e:
            logger.warning("[Rerank] 重排序失败: %s", e)

        return results

    def search(
        self,
        query: str,
        top_k: int = 5,
        use_native: bool = True,
        use_rerank: bool = True,
        rerank_score_gap: float = 0,
    ) -> List[Dict[str, Any]]:
        """
        混合检索主流程

        Args:
            query: 查询文本
            top_k: 返回结果数量
            use_native: 是否使用 Qdrant 原生 Hybrid Search
            use_rerank: 是否使用 Rerank 重排序
            rerank_score_gap: Rerank 分数差距阈值，>0 时裁剪离群结果
        """
        logger.info(
            "开始混合检索: query='%s', top_k=%d, native=%s",
            query, top_k, use_native,
        )

        results: List[Dict[str, Any]] = []

        # Build novel_id to novel_name mapping from trees
        novel_id_to_name = {v["novel_id"]: k for k, v in self.trees.items()}

        if use_native:
            hybrid_results = self.hybrid_search_native(query, top_k=top_k)

            for node_id, score, _, novel_id in hybrid_results:
                novel_name = novel_id_to_name.get(novel_id, novel_id)

                # 按需从 OSS 获取章节内容
                content = self._load_corpus_item(novel_id, node_id)

                # 从 Tree 获取节点信息
                tree_node = self._get_tree_node(novel_name, node_id)

                if not tree_node:
                    tree_node = {"title": "", "summary": ""}

                results.append({
                    "node_id": node_id,
                    "novel_id": novel_id,
                    "novel_name": novel_name,
                    "score": score,
                    "content": content,
                    "tree_node": tree_node,
                })

        # Rerank
        if use_rerank:
            results = self._rerank(query, results, score_gap=rerank_score_gap)

        logger.info("检索完成! 返回 %d 个结果", len(results))

        return results[:top_k]
