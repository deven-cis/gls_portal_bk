from pathlib import Path
from typing import Optional

from src.core.config import config


def _normalize_upload_relative_path(file_path: str) -> str:
    """
    Normalize persisted file paths to a URL path shape that can be served.
    Example:
      - "uploads/witness_videos/a.mp4" -> "uploads/witness_videos/a.mp4"
      - "/abs/path/.../uploads/witness_videos/a.mp4" -> "uploads/witness_videos/a.mp4"
    """
    raw = (file_path or "").strip()
    if not raw:
        raise ValueError("file_path is required")

    if raw.startswith("http://") or raw.startswith("https://"):
        return raw

    posix_path = Path(raw).as_posix()
    upload_segment = "/uploads/"
    if upload_segment in posix_path:
        return f"uploads/{posix_path.split(upload_segment, 1)[1]}"

    if posix_path.startswith("uploads/"):
        return posix_path

    return posix_path.lstrip("/")


def _join_url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


def build_video_download_url(file_path: str, request_base_url: Optional[str] = None) -> str:
    """
    Build a browser-downloadable URL for a stored video path.
    Current behavior:
      - local backend => API/static URL
      - future CDN/S3 => CDN URL (drop-in by config)
    """
    normalized = _normalize_upload_relative_path(file_path)
    if normalized.startswith("http://") or normalized.startswith("https://"):
        return normalized

    storage_backend = (config.STORAGE_BACKEND or "local").strip().lower()
    cdn_base = (config.CDN_BASE_URL or "").strip()
    if storage_backend in {"s3", "cdn", "r2", "gcs"} and cdn_base:
        return _join_url(cdn_base, normalized)

    base_url = (
        (request_base_url or "").strip()
        or (config.PUBLIC_API_BASE_URL or "").strip()
        or "http://127.0.0.1:8000"
    )
    return _join_url(base_url, normalized)
