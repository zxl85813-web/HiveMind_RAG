import os

_MAGIC_NUMBERS = {
    b'%PDF': 'application/pdf',
    b'\x50\x4B\x03\x04': 'application/zip', # DOCX/XLSX/PPTX 等基于 zip 的 Office 文件
    b'\x89PNG\r\n\x1a\n': 'image/png',
    b'\xff\xd8\xff': 'image/jpeg',
}

def get_file_size_human(size_in_bytes: int) -> str:
    """
    将占用字节数转换为人可读的尺寸 (如 1.5 MB, 500 KB)。
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.1f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.1f} PB"

def sniff_mime_type_from_header(file_path: str) -> str:
    """
    通过读取文件头的“魔数” (Magic Number) 推断真实的 MIME 类型，防止扩展名被恶意篡改。
    如果不匹配预置魔数，返回 'application/octet-stream'。
    """
    try:
        with open(file_path, 'rb') as f:
            header = f.read(8)
            for magic, mime in _MAGIC_NUMBERS.items():
                if header.startswith(magic):
                    return mime
    except IOError:
        pass
    
    return 'application/octet-stream'

def sanitize_filename(filename: str) -> str:
    """
    清理文件名中的非法字符，防止路径遍历攻击 (Path Traversal)。
    """
    basename = os.path.basename(filename)
    # 替换或移除潜在的危险字符，简化为基本替换
    safe_name = "".join(c for c in basename if c.isalnum() or c in " ._-")
    return safe_name.strip()
