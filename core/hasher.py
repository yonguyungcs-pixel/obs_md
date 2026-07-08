"""
core/hasher.py — SHA256 文件内容哈希计算

使用内容哈希（而非修改时间）判断文件是否真正变化，避免无意义的重复转换。
"""

import hashlib
from pathlib import Path


CHUNK_SIZE = 65536  # 64 KB


def compute_file_hash(path: Path) -> str:
    """
    计算文件的 SHA256 哈希值。

    Args:
        path: 文件路径

    Returns:
        格式为 'sha256:<hex_digest>' 的哈希字符串

    Raises:
        FileNotFoundError: 文件不存在
        PermissionError: 无读取权限
        OSError: 其他 IO 错误
    """
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            sha256.update(chunk)
    return f"sha256:{sha256.hexdigest()}"


def hash_changed(path: Path, stored_hash: str | None) -> bool:
    """
    判断文件内容是否相对于存储的哈希发生了变化。

    Args:
        path: 文件路径
        stored_hash: 上次记录的哈希值，None 表示从未处理过

    Returns:
        True 表示需要重新转换，False 表示内容未变无需处理
    """
    if stored_hash is None:
        return True
    try:
        current = compute_file_hash(path)
        return current != stored_hash
    except OSError:
        # 文件读取失败时，保守地认为需要重新处理
        return True
