from datetime import timedelta
from pathlib import Path
from typing import Dict

from sqlalchemy.orm import Session

from src.core.logger import logger
from src.uploaded_videos.models import UploadedVideos


def cleanup_expired_uploaded_videos(db: Session, now, source: str = "unknown") -> Dict[str, int]:
    cleanup_cutoff = now - timedelta(hours=1)
    cleanup_statuses = ("initialized", "uploading", "uploaded", "completed", "attach_failed")

    expired_uploads = (
        db.query(UploadedVideos)
        .filter(
            UploadedVideos.is_archived == False,
            UploadedVideos.attached_at.is_(None),
            UploadedVideos.witness_video_id.is_(None),
            UploadedVideos.expires_at.isnot(None),
            UploadedVideos.expires_at < cleanup_cutoff,
            UploadedVideos.status.in_(cleanup_statuses),
        )
        .with_for_update(skip_locked=True)
        .all()
    )

    deleted_files = 0
    archived_uploads = 0

    for upload in expired_uploads:
        for file_path in [upload.temp_file_path, upload.final_file_path]:
            if file_path and Path(file_path).exists():
                try:
                    Path(file_path).unlink()
                    deleted_files += 1
                except Exception:
                    logger.warning("Failed to delete expired upload file %s", file_path, exc_info=True)

        upload.is_archived = True
        upload.status = "expired"
        upload.last_modified_at = now
        archived_uploads += 1

    if archived_uploads:
        logger.info(
            "[%s] Expired upload cleanup completed: archived_uploads=%s deleted_files=%s cutoff=%s",
            source,
            archived_uploads,
            deleted_files,
            cleanup_cutoff,
        )
    else:
        logger.info("[%s] Expired upload cleanup found no stale uploads before cutoff %s", source, cleanup_cutoff)

    return {
        "archived_uploads": archived_uploads,
        "deleted_files": deleted_files,
    }
