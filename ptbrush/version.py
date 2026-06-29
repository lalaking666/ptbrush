from pathlib import Path

_VERSION_FILE = Path(__file__).resolve().parent / "VERSION"
_FALLBACK_VERSION = "0.0.0"


def get_version() -> str:
    """从 VERSION 文件读取版本号，文件不存在时返回 0.0.0。"""
    try:
        return _VERSION_FILE.read_text().strip()
    except (FileNotFoundError, OSError):
        return _FALLBACK_VERSION
