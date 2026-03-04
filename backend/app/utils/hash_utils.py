import hashlib
from typing import Optional

def calculate_file_hash(file_path: str, chunk_size: int = 8192) -> Optional[str]:
    """
    计算并在给定路径的文件上生成 SHA-256 哈希值。
    主要用于文档去重验证。
    """
    try:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(chunk_size), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except IOError:
        return None

def calculate_text_hash(content: str) -> str:
    """
    为纯文本内容计算 SHA-256 哈希值。
    可用于 Chunk 级或内联文本级去重。
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def verify_token_signature(token: str, secret: str = "salt") -> bool:
    """
    提供一种简单快速但安全的令牌/ID 签名校验方式，防止简单的篡改（如 URL 里的 invite 码）。
    依赖系统或配置中的全局 Secret 为盐。
    注意：涉及高强度加密的请使用 `app.auth.security` (bcrypt/jwt)。
    """
    pass # 留作占位，视需要实现
