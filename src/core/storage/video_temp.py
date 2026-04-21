import tempfile
from pathlib import Path

from src.core.config import config


def get_video_merge_temp_root() -> Path:
    temp_dir = (config.VIDEO_MERGE_TEMP_DIR or "").strip()
    return Path(temp_dir) if temp_dir else Path(tempfile.gettempdir())


def make_video_merge_temp_dir(prefix: str) -> Path:
    root = get_video_merge_temp_root()
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=root))
