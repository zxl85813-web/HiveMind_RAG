"""
StorageService — 统一文件存储抽象层。

支持两种后端：
  - S3（AWS / 兼容服务）：生产推荐，通过 settings.S3_ENABLED 自动启用
  - 本地磁盘：开发/降级备用，文件写入 settings.UPLOAD_DIR

对外接口保持一致，调用方无需感知底层存储类型。

主要功能：
  upload_file()        — 上传单个文件，返回 storage_path（S3 key 或本地路径）
  upload_file_obj()    — 上传 file-like 对象（用于批量上传）
  get_presigned_url()  — 生成预签名下载 URL（S3 专用，本地降级返回 None）
  delete_file()        — 删除文件
  get_file_stream()    — 获取文件内容流（用于索引管道读取）
"""

import hashlib
import io
import uuid
from pathlib import Path
from typing import AsyncIterator, BinaryIO

import aiofiles
from loguru import logger

from app.sdk.core.config import settings


class StorageService:
    """统一存储服务，S3 优先，本地磁盘降级。"""

    # ── 内部：获取 boto3 S3 客户端（懒加载，避免无 boto3 时启动报错）──────────
    @staticmethod
    def _get_s3_client():
        try:
            import boto3
        except ImportError:
            raise RuntimeError("boto3 未安装，请运行: pip install boto3")

        return boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION,
            endpoint_url=settings.AWS_S3_ENDPOINT_URL or None,
        )

    # ── 内部：构造 S3 对象键 ────────────────────────────────────────────────
    @staticmethod
    def _build_s3_key(filename: str, folder_path: str | None = None) -> str:
        """
        构造 S3 对象键。
        folder_path 保留原始目录结构，例如 '技术文档/2024/API设计'。
        最终键格式：{prefix}{folder_path}/{uuid}_{filename}
        """
        prefix = settings.AWS_S3_PREFIX.rstrip("/")
        unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
        if folder_path:
            # 规范化路径分隔符，去掉首尾斜杠
            clean_folder = folder_path.strip("/").replace("\\", "/")
            return f"{prefix}/{clean_folder}/{unique_name}"
        return f"{prefix}/{unique_name}"

    # ── 公开接口 ────────────────────────────────────────────────────────────

    @staticmethod
    async def upload_file(
        file_content: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        folder_path: str | None = None,
    ) -> tuple[str, int, str | None]:
        """
        上传文件内容（bytes）。

        Returns:
            (storage_path, file_size, content_hash)
            storage_path: S3 key（如 uploads/docs/xxx.pdf）或本地绝对路径
            file_size: 字节数
            content_hash: MD5 hex，用于去重
        """
        file_size = len(file_content)
        content_hash = hashlib.md5(file_content).hexdigest()

        if settings.S3_ENABLED:
            s3_key = StorageService._build_s3_key(filename, folder_path)
            try:
                s3 = StorageService._get_s3_client()
                s3.put_object(
                    Bucket=settings.AWS_S3_BUCKET_NAME,
                    Key=s3_key,
                    Body=file_content,
                    ContentType=content_type,
                )
                logger.info(f"[Storage] S3 upload OK: s3://{settings.AWS_S3_BUCKET_NAME}/{s3_key}")
                return s3_key, file_size, content_hash
            except Exception as e:
                logger.error(f"[Storage] S3 upload failed, falling back to local: {e}")
                # 降级到本地存储

        # 本地存储降级
        upload_dir = settings.UPLOAD_DIR
        if folder_path:
            upload_dir = upload_dir / folder_path.strip("/").replace("\\", "/")
        upload_dir.mkdir(parents=True, exist_ok=True)

        unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
        local_path = upload_dir / unique_name
        async with aiofiles.open(local_path, "wb") as f:
            await f.write(file_content)

        logger.info(f"[Storage] Local upload OK: {local_path}")
        return str(local_path), file_size, content_hash

    @staticmethod
    async def upload_file_stream(
        file_obj: BinaryIO,
        filename: str,
        content_type: str = "application/octet-stream",
        folder_path: str | None = None,
        chunk_size: int = 1024 * 1024,  # 1MB
    ) -> tuple[str, int, str | None]:
        """
        流式上传（适合大文件，避免一次性读入内存）。
        先读取到内存计算 hash，再上传。大文件（>100MB）建议用预签名 URL 直传。
        """
        buf = io.BytesIO()
        hasher = hashlib.md5()
        while True:
            chunk = file_obj.read(chunk_size)
            if not chunk:
                break
            buf.write(chunk)
            hasher.update(chunk)

        content = buf.getvalue()
        content_hash = hasher.hexdigest()
        file_size = len(content)

        if settings.S3_ENABLED:
            s3_key = StorageService._build_s3_key(filename, folder_path)
            try:
                s3 = StorageService._get_s3_client()
                s3.put_object(
                    Bucket=settings.AWS_S3_BUCKET_NAME,
                    Key=s3_key,
                    Body=content,
                    ContentType=content_type,
                )
                logger.info(f"[Storage] S3 stream upload OK: {s3_key} ({file_size} bytes)")
                return s3_key, file_size, content_hash
            except Exception as e:
                logger.error(f"[Storage] S3 stream upload failed, falling back to local: {e}")

        # 本地降级
        upload_dir = settings.UPLOAD_DIR
        if folder_path:
            upload_dir = upload_dir / folder_path.strip("/").replace("\\", "/")
        upload_dir.mkdir(parents=True, exist_ok=True)
        unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
        local_path = upload_dir / unique_name
        async with aiofiles.open(local_path, "wb") as f:
            await f.write(content)
        return str(local_path), file_size, content_hash

    @staticmethod
    def get_presigned_url(storage_path: str, expires_in: int | None = None) -> str | None:
        """
        生成预签名下载 URL（S3 专用）。
        本地存储返回 None，调用方需自行处理（如通过 /preview 接口代理）。
        """
        if not settings.S3_ENABLED:
            return None

        # 判断是否是 S3 key（不以 / 或盘符开头）
        if storage_path.startswith("/") or (len(storage_path) > 1 and storage_path[1] == ":"):
            return None  # 本地路径

        try:
            s3 = StorageService._get_s3_client()
            url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.AWS_S3_BUCKET_NAME, "Key": storage_path},
                ExpiresIn=expires_in or settings.AWS_S3_PRESIGN_EXPIRES,
            )
            return url
        except Exception as e:
            logger.error(f"[Storage] Presign failed for {storage_path}: {e}")
            return None

    @staticmethod
    async def get_file_bytes(storage_path: str) -> bytes:
        """
        读取文件内容（用于索引管道）。
        S3 key → 从 S3 下载；本地路径 → 读本地文件。
        """
        is_local = storage_path.startswith("/") or (len(storage_path) > 1 and storage_path[1] == ":")

        if not is_local and settings.S3_ENABLED:
            try:
                s3 = StorageService._get_s3_client()
                resp = s3.get_object(Bucket=settings.AWS_S3_BUCKET_NAME, Key=storage_path)
                return resp["Body"].read()
            except Exception as e:
                logger.error(f"[Storage] S3 get failed for {storage_path}: {e}")
                raise

        # 本地文件
        async with aiofiles.open(storage_path, "rb") as f:
            return await f.read()

    @staticmethod
    async def delete_file(storage_path: str) -> bool:
        """删除文件（S3 或本地）。"""
        is_local = storage_path.startswith("/") or (len(storage_path) > 1 and storage_path[1] == ":")

        if not is_local and settings.S3_ENABLED:
            try:
                s3 = StorageService._get_s3_client()
                s3.delete_object(Bucket=settings.AWS_S3_BUCKET_NAME, Key=storage_path)
                logger.info(f"[Storage] S3 delete OK: {storage_path}")
                return True
            except Exception as e:
                logger.error(f"[Storage] S3 delete failed for {storage_path}: {e}")
                return False

        try:
            Path(storage_path).unlink(missing_ok=True)
            return True
        except Exception as e:
            logger.error(f"[Storage] Local delete failed for {storage_path}: {e}")
            return False

    @staticmethod
    def generate_presigned_upload_url(
        filename: str,
        folder_path: str | None = None,
        content_type: str = "application/octet-stream",
        expires_in: int = 3600,
    ) -> dict | None:
        """
        生成预签名上传 URL（用于前端直传大文件到 S3，绕过后端）。

        Returns:
            {"url": ..., "fields": ..., "s3_key": ...}  — 前端用 multipart/form-data POST
            None — S3 未配置
        """
        if not settings.S3_ENABLED:
            return None

        s3_key = StorageService._build_s3_key(filename, folder_path)
        try:
            s3 = StorageService._get_s3_client()
            presigned = s3.generate_presigned_post(
                Bucket=settings.AWS_S3_BUCKET_NAME,
                Key=s3_key,
                Fields={"Content-Type": content_type},
                Conditions=[
                    {"Content-Type": content_type},
                    ["content-length-range", 1, 500 * 1024 * 1024],  # 最大 500MB
                ],
                ExpiresIn=expires_in,
            )
            presigned["s3_key"] = s3_key
            return presigned
        except Exception as e:
            logger.error(f"[Storage] Presigned upload URL generation failed: {e}")
            return None

    # ── S3 Multipart Upload（断点续传）────────────────────────────────────────

    @staticmethod
    def create_multipart_upload(
        filename: str,
        folder_path: str | None = None,
        content_type: str = "application/octet-stream",
    ) -> dict | None:
        """
        初始化 S3 Multipart Upload，返回 upload_id 和 s3_key。
        前端保存 upload_id 到 localStorage，断网后可续传。

        Returns:
            {"upload_id": "...", "s3_key": "uploads/..."}
            None — S3 未配置
        """
        if not settings.S3_ENABLED:
            return None

        s3_key = StorageService._build_s3_key(filename, folder_path)
        try:
            s3 = StorageService._get_s3_client()
            resp = s3.create_multipart_upload(
                Bucket=settings.AWS_S3_BUCKET_NAME,
                Key=s3_key,
                ContentType=content_type,
            )
            upload_id = resp["UploadId"]
            logger.info(f"[Storage] Multipart upload created: {s3_key} (upload_id={upload_id[:8]}...)")
            return {"upload_id": upload_id, "s3_key": s3_key}
        except Exception as e:
            logger.error(f"[Storage] create_multipart_upload failed: {e}")
            return None

    @staticmethod
    def generate_presigned_part_url(
        s3_key: str,
        upload_id: str,
        part_number: int,
        expires_in: int = 3600,
    ) -> str | None:
        """
        为指定分片生成预签名 PUT URL。
        前端直接 PUT 到该 URL，后端不承受分片数据流量。

        part_number: 1-based，S3 要求 1~10000
        """
        if not settings.S3_ENABLED:
            return None
        try:
            s3 = StorageService._get_s3_client()
            url = s3.generate_presigned_url(
                "upload_part",
                Params={
                    "Bucket": settings.AWS_S3_BUCKET_NAME,
                    "Key": s3_key,
                    "UploadId": upload_id,
                    "PartNumber": part_number,
                },
                ExpiresIn=expires_in,
            )
            return url
        except Exception as e:
            logger.error(f"[Storage] generate_presigned_part_url failed: {e}")
            return None

    @staticmethod
    def complete_multipart_upload(
        s3_key: str,
        upload_id: str,
        parts: list[dict],  # [{"PartNumber": 1, "ETag": "..."}, ...]
    ) -> dict | None:
        """
        合并所有分片，完成 Multipart Upload。

        Returns:
            {"s3_key": ..., "etag": ..., "location": ...}
            None — 失败
        """
        if not settings.S3_ENABLED:
            return None
        try:
            s3 = StorageService._get_s3_client()
            resp = s3.complete_multipart_upload(
                Bucket=settings.AWS_S3_BUCKET_NAME,
                Key=s3_key,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts},
            )
            logger.info(f"[Storage] Multipart upload completed: {s3_key}")
            return {
                "s3_key": s3_key,
                "etag": resp.get("ETag", "").strip('"'),
                "location": resp.get("Location", ""),
            }
        except Exception as e:
            logger.error(f"[Storage] complete_multipart_upload failed: {e}")
            return None

    @staticmethod
    def abort_multipart_upload(s3_key: str, upload_id: str) -> bool:
        """
        中止 Multipart Upload，清理 S3 上的临时分片（避免产生存储费用）。
        """
        if not settings.S3_ENABLED:
            return False
        try:
            s3 = StorageService._get_s3_client()
            s3.abort_multipart_upload(
                Bucket=settings.AWS_S3_BUCKET_NAME,
                Key=s3_key,
                UploadId=upload_id,
            )
            logger.info(f"[Storage] Multipart upload aborted: {s3_key}")
            return True
        except Exception as e:
            logger.error(f"[Storage] abort_multipart_upload failed: {e}")
            return False

    @staticmethod
    def list_uploaded_parts(s3_key: str, upload_id: str) -> list[dict]:
        """
        查询已上传的分片列表（用于断点续传时跳过已完成的分片）。

        Returns:
            [{"PartNumber": 1, "ETag": "...", "Size": 5242880}, ...]
        """
        if not settings.S3_ENABLED:
            return []
        try:
            s3 = StorageService._get_s3_client()
            parts = []
            kwargs: dict = {
                "Bucket": settings.AWS_S3_BUCKET_NAME,
                "Key": s3_key,
                "UploadId": upload_id,
            }
            while True:
                resp = s3.list_parts(**kwargs)
                parts.extend(resp.get("Parts", []))
                if resp.get("IsTruncated"):
                    kwargs["PartNumberMarker"] = resp["NextPartNumberMarker"]
                else:
                    break
            return [
                {"PartNumber": p["PartNumber"], "ETag": p["ETag"].strip('"'), "Size": p["Size"]}
                for p in parts
            ]
        except Exception as e:
            logger.error(f"[Storage] list_uploaded_parts failed: {e}")
            return []


# 单例
storage_service = StorageService()
