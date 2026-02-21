"""
文件存储抽象层。

提供统一的文件存储接口，后端可插拔切换:
    - LocalStorage  (开发环境)
    - MinIOStorage  (生产环境)

用法:
    from app.core.storage import get_storage
    storage = get_storage()
    url = await storage.upload(file, path="documents/xxx.pdf")

参见: REGISTRY.md > 后端 > 核心配置 > storage
"""

import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO

from app.core.config import settings
from app.core.logging import logger


class StorageBackend(ABC):
    """文件存储抽象基类 — 所有存储后端必须实现此接口。"""

    @abstractmethod
    async def upload(self, file: BinaryIO, path: str, content_type: str = "") -> str:
        """
        上传文件。

        Args:
            file: 文件对象
            path: 存储路径 (如 "documents/abc.pdf")
            content_type: MIME 类型

        Returns:
            文件访问 URL
        """

    @abstractmethod
    async def download(self, path: str) -> bytes:
        """下载文件内容。"""

    @abstractmethod
    async def delete(self, path: str) -> bool:
        """删除文件。"""

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """检查文件是否存在。"""

    @staticmethod
    def generate_unique_path(original_filename: str, prefix: str = "") -> str:
        """
        生成唯一存储路径，避免文件名冲突。

        Args:
            original_filename: 原始文件名
            prefix: 路径前缀 (如 "documents", "avatars")

        Returns:
            唯一路径 (如 "documents/a1b2c3d4_report.pdf")
        """
        unique_id = uuid.uuid4().hex[:8]
        safe_name = Path(original_filename).name  # 防止路径穿越
        path = f"{unique_id}_{safe_name}"
        if prefix:
            path = f"{prefix}/{path}"
        return path


class LocalStorage(StorageBackend):
    """本地文件存储 — 开发环境使用。"""

    def __init__(self, base_dir: str = "storage"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info("LocalStorage initialized: {}", self.base_dir.absolute())

    async def upload(self, file: BinaryIO, path: str, content_type: str = "") -> str:
        full_path = self.base_dir / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(file.read())
        logger.debug("File uploaded to local: {}", path)
        return f"/storage/{path}"

    async def download(self, path: str) -> bytes:
        full_path = self.base_dir / path
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return full_path.read_bytes()

    async def delete(self, path: str) -> bool:
        full_path = self.base_dir / path
        if full_path.exists():
            full_path.unlink()
            logger.debug("File deleted from local: {}", path)
            return True
        return False

    async def exists(self, path: str) -> bool:
        return (self.base_dir / path).exists()


class MinIOStorage(StorageBackend):
    """
    MinIO 对象存储 — 生产环境使用。

    TODO: 实现 MinIO 连接和操作
    依赖: pip install miniopy-async
    """

    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str):
        self.endpoint = endpoint
        self.bucket = bucket
        # TODO: 初始化 miniopy-async 客户端
        logger.info("MinIOStorage initialized: {}/{}", endpoint, bucket)

    async def upload(self, file: BinaryIO, path: str, content_type: str = "") -> str:
        # TODO: 实现 MinIO 上传
        raise NotImplementedError("MinIO upload not yet implemented")

    async def download(self, path: str) -> bytes:
        # TODO: 实现 MinIO 下载
        raise NotImplementedError("MinIO download not yet implemented")

    async def delete(self, path: str) -> bool:
        # TODO: 实现 MinIO 删除
        raise NotImplementedError("MinIO delete not yet implemented")

    async def exists(self, path: str) -> bool:
        # TODO: 实现 MinIO 存在性检查
        raise NotImplementedError("MinIO exists not yet implemented")


# === SingleTon Factory ===
_storage_instance: StorageBackend | None = None


def get_storage() -> StorageBackend:
    """
    获取存储后端实例 (单例)。

    根据 settings.STORAGE_BACKEND 自动选择。
    """
    global _storage_instance
    if _storage_instance is None:
        backend = getattr(settings, "STORAGE_BACKEND", "local")
        if backend == "minio":
            _storage_instance = MinIOStorage(
                endpoint=getattr(settings, "MINIO_ENDPOINT", "localhost:9000"),
                access_key=getattr(settings, "MINIO_ACCESS_KEY", "minioadmin"),
                secret_key=getattr(settings, "MINIO_SECRET_KEY", "minioadmin"),
                bucket=getattr(settings, "MINIO_BUCKET", "hivemind"),
            )
        else:
            _storage_instance = LocalStorage()
    return _storage_instance
