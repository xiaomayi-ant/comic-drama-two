"""
Embedding 客户端：调用本地 BGE-M3 模型生成向量
"""

import os
import logging
from typing import List, Optional

from dotenv import load_dotenv
import requests

load_dotenv()

logger = logging.getLogger(__name__)


class EmbeddingClient:
    """Embedding 客户端"""

    def __init__(self):
        self.api_base = os.getenv("EMBEDDING_API_BASE", "http://localhost:11434/v1")
        self.api_key = os.getenv("EMBEDDING_API_KEY", "ollama")
        self.model_name = os.getenv("EMBEDDING_MODEL_NAME", "bge-m3")
        self.dimension = int(os.getenv("EMBEDDING_MODEL_DIMENSION", "1024"))
        self.timeout = int(os.getenv("EMBEDDING_TIMEOUT", "300"))
        self.batch_size = int(os.getenv("EMBEDDING_BATCH_SIZE", "10"))

    def embed(self, text: str) -> Optional[List[float]]:
        """生成单个文本的向量"""
        return self.embed_batch([text])[0] if text else None

    def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """批量生成向量（自动分批处理）"""
        if not texts:
            return []

        all_embeddings = []
        total_batches = (len(texts) + self.batch_size - 1) // self.batch_size

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1

            try:
                response = requests.post(
                    f"{self.api_base}/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model_name,
                        "input": batch,
                    },
                    timeout=self.timeout,
                )
                response.raise_for_status()

                data = response.json()
                embeddings = [item["embedding"] for item in data.get("data", [])]

                if len(embeddings) != len(batch):
                    logger.warning(
                        "批次 %d/%d: 返回向量数 %d != 请求数 %d",
                        batch_num, total_batches, len(embeddings), len(batch),
                    )
                    embeddings.extend([None] * (len(batch) - len(embeddings)))

                all_embeddings.extend(embeddings)
                logger.debug(
                    "批次 %d/%d: 成功生成 %d 个向量",
                    batch_num, total_batches, len(embeddings),
                )

            except requests.exceptions.Timeout:
                logger.error(
                    "批次 %d/%d: 超时 (%d秒)，尝试单独处理",
                    batch_num, total_batches, self.timeout,
                )
                for text in batch:
                    all_embeddings.append(self._embed_single_with_retry(text))

            except Exception as e:
                logger.error("批次 %d/%d: 失败 - %s", batch_num, total_batches, e)
                all_embeddings.extend([None] * len(batch))

        success_count = sum(1 for e in all_embeddings if e is not None)
        logger.info(
            "生成向量: %d/%d 成功, 维度=%d",
            success_count,
            len(texts),
            len(all_embeddings[0]) if all_embeddings and all_embeddings[0] else 0,
        )

        return all_embeddings

    def _embed_single_with_retry(
        self, text: str, max_retries: int = 3
    ) -> Optional[List[float]]:
        """单个文本生成向量（带重试）"""
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.api_base}/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model_name,
                        "input": [text[:8000]],
                    },
                    timeout=60,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("data", [{}])[0].get("embedding")
            except Exception as e:
                logger.warning("单个向量化重试 %d/%d: %s", attempt + 1, max_retries, e)
                if attempt == max_retries - 1:
                    logger.error("单个向量化最终失败: 文本长度=%d", len(text))
                    return None

    def get_dimension(self) -> int:
        """获取向量维度"""
        return self.dimension


embedding_client = EmbeddingClient()
