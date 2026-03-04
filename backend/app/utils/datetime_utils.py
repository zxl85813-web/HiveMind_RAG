from datetime import datetime, timezone

def utc_now() -> datetime:
    """获取当前时间的 UTC datetime，带有 tzinfo。"""
    return datetime.now(timezone.utc)

def format_iso8601(dt: datetime) -> str:
    """
    将 datetime 格式化为标准的 ISO 8601 字符串。
    如果 datetime 没有时区信息 (naive)，会假定其为 UTC 并添加 Z 后缀。
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat(timespec='milliseconds')

def parse_iso8601(timestamp_str: str) -> datetime:
    """
    将 ISO 8601 字符串解析为 datetime 对象。
    总是返回带时区信息的 datetime (未指定则默认为 UTC)。
    """
    # 兼容尾部的 Z 标记
    if timestamp_str.endswith("Z"):
        timestamp_str = timestamp_str[:-1] + "+00:00"
    
    dt = datetime.fromisoformat(timestamp_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
