"""
检索集成分步测试脚本

使用方式:
    cd backend
    # 测试全部:
    python -m tests.test_retrieval

    # 只测某一步:
    python -m tests.test_retrieval --step 1   # Qdrant
    python -m tests.test_retrieval --step 2   # MongoDB
    python -m tests.test_retrieval --step 3   # Ollama Embedding
    python -m tests.test_retrieval --step 4   # OSS
    python -m tests.test_retrieval --step 5   # 完整检索
"""

import argparse
import logging
import os
import sys

# 确保 backend/ 为根路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("test_retrieval")

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"


def step1_qdrant():
    """Step 1: 测试 Qdrant 连接"""
    logger.info("=" * 50)
    logger.info("Step 1: 测试 Qdrant 连接")
    logger.info("=" * 50)

    try:
        from qdrant_client import QdrantClient

        host = os.getenv("QDRANT_HOST", "localhost")
        port = int(os.getenv("QDRANT_PORT", "6333"))
        collection = os.getenv("QDRANT_COLLECTION", "novel_nodes_hybrid")

        client = QdrantClient(host=host, port=port, timeout=5)

        # 检查集合是否存在
        collections = client.get_collections().collections
        names = [c.name for c in collections]
        logger.info("Qdrant 已连接, 集合列表: %s", names)

        if collection in names:
            info = client.get_collection(collection)
            logger.info(
                "集合 '%s' 存在: %d 个向量, 向量维度=%s",
                collection,
                info.points_count,
                info.config.params.vectors,
            )
        else:
            logger.warning("集合 '%s' 不存在! 可用集合: %s", collection, names)
            return FAIL

        # 尝试 scroll 几条数据看看 payload 结构
        points, _ = client.scroll(
            collection_name=collection, limit=2, with_payload=True, with_vectors=False
        )
        if points:
            logger.info("示例 payload keys: %s", list(points[0].payload.keys()))
            logger.info(
                "示例: novel_id=%s, node_id=%s",
                points[0].payload.get("novel_id"),
                points[0].payload.get("node_id"),
            )
        else:
            logger.warning("集合为空，没有数据")
            return FAIL

        return PASS

    except Exception as e:
        logger.error("Qdrant 连接失败: %s", e)
        return FAIL


def step2_mongodb():
    """Step 2: 测试 MongoDB 连接"""
    logger.info("=" * 50)
    logger.info("Step 2: 测试 MongoDB 连接")
    logger.info("=" * 50)

    try:
        from pymongo import MongoClient

        uri = os.getenv("MONGODB_URI", "mongodb://admin:susie2026@localhost:27017")
        db_name = os.getenv("MONGODB_DATABASE", "novels")

        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        # 触发实际连接
        client.admin.command("ping")
        logger.info("MongoDB 已连接: %s", uri.split("@")[-1])

        db = client[db_name]
        collections = db.list_collection_names()
        logger.info("数据库 '%s' 的集合: %s", db_name, collections)

        if "trees" in collections:
            count = db.trees.count_documents({})
            logger.info("trees 集合: %d 条文档", count)

            sample = db.trees.find_one()
            if sample:
                logger.info(
                    "示例 tree: novel_id=%s, novel_name=%s, nodes=%d",
                    sample.get("novel_id"),
                    sample.get("novel_name"),
                    len(sample.get("tree_structure", {}).get("structure", [])),
                )
        else:
            logger.warning("'trees' 集合不存在")
            return FAIL

        return PASS

    except Exception as e:
        logger.error("MongoDB 连接失败: %s", e)
        return FAIL


def step3_embedding():
    """Step 3: 测试 Ollama Embedding 服务"""
    logger.info("=" * 50)
    logger.info("Step 3: 测试 Embedding 服务 (Ollama)")
    logger.info("=" * 50)

    try:
        from src.retrieval.embedding_client import EmbeddingClient

        client = EmbeddingClient()
        logger.info(
            "Embedding 配置: api_base=%s, model=%s, dim=%d",
            client.api_base,
            client.model_name,
            client.dimension,
        )

        test_text = "武侠小说中的修炼境界"
        vector = client.embed(test_text)

        if vector and len(vector) > 0:
            logger.info(
                "Embedding 成功! 维度=%d, 前5维: %s",
                len(vector),
                [round(v, 4) for v in vector[:5]],
            )
            return PASS
        else:
            logger.error("Embedding 返回空向量")
            return FAIL

    except Exception as e:
        logger.error("Embedding 失败: %s", e)
        return FAIL


def step4_oss():
    """Step 4: 测试 OSS 连接"""
    logger.info("=" * 50)
    logger.info("Step 4: 测试 OSS 连接")
    logger.info("=" * 50)

    try:
        from src.retrieval.oss_manager import OSSManager

        mgr = OSSManager()

        if not mgr.is_configured:
            logger.warning("OSS 未配置或未启用, 跳过测试")
            return SKIP

        logger.info(
            "OSS 配置: bucket=%s, endpoint=%s",
            mgr.bucket_name,
            mgr.endpoint,
        )

        # 列出 novels/ 前缀下的前 5 个文件
        objects = mgr.list_objects(prefix="novels/structured/", limit=5)
        logger.info("novels/structured/ 下有 %d 个对象 (limit=5)", len(objects))
        for obj in objects[:3]:
            logger.info("  %s (%d bytes)", obj["key"], obj["size"])

        if objects:
            # 尝试下载一个小文件内容
            test_key = objects[0]["key"]
            content = mgr.download_content(test_key)
            logger.info(
                "下载测试: %s -> %d 字符, 前100字: %s",
                test_key,
                len(content),
                content[:100],
            )
            return PASS
        else:
            logger.warning("OSS 中无数据，但连接正常")
            return PASS

    except Exception as e:
        logger.error("OSS 测试失败: %s", e)
        return FAIL


def step5_full_search():
    """Step 5: 完整检索测试"""
    logger.info("=" * 50)
    logger.info("Step 5: 完整检索流程测试")
    logger.info("=" * 50)

    try:
        from src.core.config import settings
        from src.retrieval.searcher import HybridSearcher

        logger.info(
            "检索配置: qdrant=%s:%d, collection=%s, top_k=%d, rerank=%s",
            settings.qdrant_host,
            settings.qdrant_port,
            settings.qdrant_collection,
            settings.retrieval_top_k,
            settings.retrieval_use_rerank,
        )

        searcher = HybridSearcher(settings)
        logger.info("HybridSearcher 初始化成功, %d 本小说", len(searcher.trees))

        query = "主角修炼突破境界"
        logger.info("执行检索: query='%s'", query)

        results = searcher.search(
            query,
            top_k=settings.retrieval_top_k,
            use_native=True,
            use_rerank=False,  # 先不开 rerank，减少依赖
        )

        if not results:
            logger.warning("检索返回 0 条结果")
            return FAIL

        logger.info("检索成功! 返回 %d 条结果:", len(results))
        for i, r in enumerate(results, 1):
            title = r.get("tree_node", {}).get("title", "N/A")
            novel = r.get("novel_name", "N/A")
            score = r.get("score", 0)
            content_len = len(r.get("content", ""))
            logger.info(
                "  %d. [%s] %s (score=%.4f, content=%d字)",
                i, novel, title, score, content_len,
            )

        return PASS

    except Exception as e:
        logger.error("完整检索失败: %s", e)
        return FAIL


def main():
    parser = argparse.ArgumentParser(description="检索集成分步测试")
    parser.add_argument(
        "--step",
        type=int,
        choices=[1, 2, 3, 4, 5],
        help="只运行指定步骤 (1=Qdrant, 2=MongoDB, 3=Embedding, 4=OSS, 5=完整检索)",
    )
    args = parser.parse_args()

    steps = [
        (1, "Qdrant 连接", step1_qdrant),
        (2, "MongoDB 连接", step2_mongodb),
        (3, "Embedding 服务", step3_embedding),
        (4, "OSS 存储", step4_oss),
        (5, "完整检索流程", step5_full_search),
    ]

    if args.step:
        steps = [(n, name, fn) for n, name, fn in steps if n == args.step]

    results = []
    for num, name, fn in steps:
        result = fn()
        results.append((num, name, result))
        logger.info("")

    # 汇总
    logger.info("=" * 50)
    logger.info("测试汇总")
    logger.info("=" * 50)
    all_pass = True
    for num, name, result in results:
        status = result
        if result == FAIL:
            all_pass = False
        logger.info("  Step %d [%s] %s", num, status, name)

    if all_pass:
        logger.info("所有测试通过!")
    else:
        logger.warning("部分测试失败，请检查对应服务")
        sys.exit(1)


if __name__ == "__main__":
    main()
