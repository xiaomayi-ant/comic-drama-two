"""
OSS 存储管理：上传/下载小说到阿里云 OSS
"""

import os
import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import oss2

load_dotenv()

logger = logging.getLogger(__name__)


class OSSManager:
    """OSS 存储管理类"""

    def __init__(self):
        self.enabled = os.getenv("OSS_ENABLED", "true").lower() in ("true", "1", "yes")
        self.access_key_id = os.getenv("OSS_ACCESS_KEY_ID", "")
        self.access_key_secret = os.getenv("OSS_ACCESS_KEY_SECRET", "")
        self.bucket_name = os.getenv("OSS_BUCKET_NAME", "")
        self.endpoint = os.getenv("OSS_ENDPOINT", "")

        # 存储路径配置
        self.prefix = os.getenv("OSS_PREFIX", "novels/")
        self.raw_prefix = os.getenv("OSS_RAW_PREFIX", "novels/raw/")
        self.structured_prefix = os.getenv("OSS_STRUCTURED_PREFIX", "novels/structured/")

        self._bucket = None

    @property
    def is_configured(self) -> bool:
        """检查 OSS 是否已配置且启用"""
        if not self.enabled:
            return False
        return all([
            self.access_key_id,
            self.access_key_secret,
            self.bucket_name,
            self.endpoint,
        ])

    @property
    def bucket(self) -> oss2.Bucket:
        """获取 Bucket 对象（延迟初始化）"""
        if self._bucket is None:
            if not self.is_configured:
                raise ValueError("OSS 未配置，请检查 .env 文件")
            auth = oss2.Auth(self.access_key_id, self.access_key_secret)
            self._bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)
            logger.info("OSS Bucket 初始化: %s", self.bucket_name)
        return self._bucket

    def upload_file(
        self,
        local_path: str,
        oss_key: Optional[str] = None,
        overwrite: bool = False,
    ) -> str:
        """上传文件到 OSS"""
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"文件不存在: {local_path}")

        if oss_key is None:
            filename = Path(local_path).name
            oss_key = f"{self.prefix}{filename}"

        if not overwrite and self.object_exists(oss_key):
            logger.warning("文件已存在，跳过上传: %s", oss_key)
            return oss_key

        result = self.bucket.put_object_from_file(oss_key, local_path)
        if result.status == 200:
            logger.info("上传成功: %s -> %s", local_path, oss_key)
        else:
            raise RuntimeError(f"上传失败: status={result.status}")

        return oss_key

    def upload_content(
        self,
        content: str,
        oss_key: str,
        overwrite: bool = False,
    ) -> str:
        """直接上传内容到 OSS"""
        if not overwrite and self.object_exists(oss_key):
            logger.warning("文件已存在，跳过上传: %s", oss_key)
            return oss_key

        result = self.bucket.put_object(oss_key, content.encode("utf-8"))
        if result.status == 200:
            logger.info("内容上传成功: %s (%d bytes)", oss_key, len(content))
        else:
            raise RuntimeError(f"上传失败: status={result.status}")

        return oss_key

    def download_file(self, oss_key: str, local_path: str) -> str:
        """从 OSS 下载文件"""
        local_dir = Path(local_path).parent
        local_dir.mkdir(parents=True, exist_ok=True)

        self.bucket.get_object_to_file(oss_key, local_path)
        logger.info("下载成功: %s -> %s", oss_key, local_path)

        return local_path

    def download_content(self, oss_key: str) -> str:
        """从 OSS 下载内容"""
        result = self.bucket.get_object(oss_key)
        content = result.read().decode("utf-8")
        logger.info("内容下载成功: %s (%d bytes)", oss_key, len(content))
        return content

    def object_exists(self, oss_key: str) -> bool:
        """检查文件是否存在"""
        return self.bucket.object_exists(oss_key)

    def delete_object(self, oss_key: str) -> bool:
        """删除文件"""
        self.bucket.delete_object(oss_key)
        logger.info("删除成功: %s", oss_key)
        return True

    def list_objects(self, prefix: Optional[str] = None, limit: int = 100) -> list:
        """列出 OSS 文件"""
        search_prefix = prefix or self.prefix
        objects = []
        for obj in oss2.ObjectIterator(self.bucket, prefix=search_prefix, max_keys=limit):
            objects.append({
                "key": obj.key,
                "size": obj.size,
                "last_modified": obj.last_modified,
            })
        logger.info("列出 %d 个文件: prefix=%s", len(objects), search_prefix)
        return objects

    def get_url(self, oss_key: str, expires: int = 3600) -> str:
        """获取临时访问 URL"""
        url = self.bucket.sign_url("GET", oss_key, expires)
        return url


oss_manager = OSSManager()
