import asyncio
import shutil
import tempfile
from pathlib import Path

from sqlalchemy.exc import DatabaseError, OperationalError, SQLAlchemyError

from src.core.celery_config import celery_app
from src.core.database import SessionLocal
from src.core.file_utils import extract_video_metadata
from src.core.logger import logger
from src.core.storage_prefixes import merged_witness_video_prefix
from src.core.storage_service import storage_service
from src.core.timezone_utils import get_timezone_now
from src.core.video_merge import (
    build_witness_merged_video_output_path,
    delete_file_if_exists,
    merge_video_files_ffmpeg,
)
from src.witnesses.models import Witnesses
from src.witness_videos.models import WitnessVideos


@celery_app.task(name='src.witnesses.tasks.generate_witness_complete_video_task')
def generate_witness_complete_video_task(witness_id: int, requested_by: int | None = None):
    session = None
    output_path = None
    temp_workspace = None
    started_at = get_timezone_now()

    try:
        logger.info('[Celery Task] Starting witness complete-video merge for witness_id=%s', witness_id)
        session = SessionLocal()
        witness = (
            session.query(Witnesses)
            .filter(Witnesses.id == witness_id, Witnesses.is_archived == False)
            .first()
        )
        if not witness:
            raise ValueError(f'Witness {witness_id} not found or archived')

        witness.merge_status = 'processing'
        witness.merge_error = None
        witness.last_modified_at = started_at
        if requested_by is not None:
            witness.last_modified_by = requested_by
        session.add(witness)
        session.commit()

        videos = (
            session.query(WitnessVideos)
            .filter(
                WitnessVideos.wit_no == witness.id,
                WitnessVideos.is_archived == False,
                WitnessVideos.file_path.isnot(None),
            )
            .order_by(WitnessVideos.id.asc())
            .all()
        )
        if not videos:
            raise ValueError('No witness videos are available to merge')

        source_paths = [video.file_path for video in videos]
        missing_videos = [
            {"video_id": video.id, "file_path": video.file_path}
            for video in videos
            if not storage_service.exists(video.file_path)
        ]
        if missing_videos:
            logger.warning(
                "[Celery Task] Witness %s merge has missing source video file(s): %s",
                witness.id,
                missing_videos,
            )
            raise ValueError(
                f"Witness {witness.id} merge cannot start because {len(missing_videos)} source video file(s) are missing"
            )

        if storage_service.is_s3:
            temp_workspace = Path(tempfile.mkdtemp(prefix=f'witness_merge_{witness.id}_'))
            staged_paths = []
            for index, video in enumerate(videos, start=1):
                source_name = video.file_name or Path(video.file_path).name or f'clip_{index}.mp4'
                source_ext = Path(source_name).suffix or '.mp4'
                staged_path = temp_workspace / f'clip_{index:03d}{source_ext}'
                storage_service.download_to_path(video.file_path, staged_path)
                staged_paths.append(str(staged_path))
            source_paths = staged_paths

        output_path = build_witness_merged_video_output_path(witness.id, witness.job_no)
        merge_video_files_ffmpeg(
            source_paths,
            output_path,
            log_label=f'witness {witness.id} job {witness.job_no}',
        )

        metadata = asyncio.run(extract_video_metadata(str(output_path)))
        output_file_size = metadata.get('file_size') or output_path.stat().st_size
        stored_output_key = str(output_path)
        stored_output_name = output_path.name
        if storage_service.is_s3:
            stored_output = storage_service.upload_path(
                output_path,
                subfolder=merged_witness_video_prefix(job_no=witness.job_no, witness_id=witness.id),
                file_name=output_path.name,
                content_type='video/mp4',
            )
            stored_output_key = stored_output.key
            stored_output_name = stored_output.file_name
            delete_file_if_exists(output_path)

        completed_at = get_timezone_now()

        witness.merged_video_path = stored_output_key
        witness.merged_video_name = stored_output_name
        witness.merged_video_size = output_file_size
        witness.merged_duration = metadata.get('duration_seconds')
        witness.merge_status = 'completed'
        witness.merge_error = None
        witness.merge_completed_at = completed_at
        witness.last_modified_at = completed_at
        if requested_by is not None:
            witness.last_modified_by = requested_by
        session.add(witness)
        session.commit()

        logger.info('[Celery Task] Witness complete-video merge finished for witness_id=%s', witness.id)
        return {
            'status': 'success',
            'witness_id': witness.id,
            'output_path': stored_output_key,
            'merged_video_name': stored_output_name,
        }

    except OperationalError as exc:
        if session:
            session.rollback()
        logger.error('[Celery Task] Database operational error during witness merge: %s', exc, exc_info=True)
        return {'status': 'error', 'error_type': 'OperationalError', 'error': str(exc), 'witness_id': witness_id}
    except DatabaseError as exc:
        if session:
            session.rollback()
        logger.error('[Celery Task] Database error during witness merge: %s', exc, exc_info=True)
        return {'status': 'error', 'error_type': 'DatabaseError', 'error': str(exc), 'witness_id': witness_id}
    except SQLAlchemyError as exc:
        if session:
            session.rollback()
        logger.error('[Celery Task] SQLAlchemy error during witness merge: %s', exc, exc_info=True)
        return {'status': 'error', 'error_type': 'SQLAlchemyError', 'error': str(exc), 'witness_id': witness_id}
    except Exception as exc:
        if session:
            session.rollback()
        logger.error('[Celery Task] Witness merge failed for witness_id=%s: %s', witness_id, exc, exc_info=True)
        if output_path is not None:
            delete_file_if_exists(output_path)
        if session:
            try:
                witness = session.query(Witnesses).filter(Witnesses.id == witness_id).first()
                if witness:
                    now = get_timezone_now()
                    witness.merged_video_path = None
                    witness.merged_video_name = None
                    witness.merged_video_size = None
                    witness.merged_duration = None
                    witness.merge_status = 'failed'
                    witness.merge_error = str(exc)
                    witness.merge_completed_at = None
                    witness.last_modified_at = now
                    if requested_by is not None:
                        witness.last_modified_by = requested_by
                    session.add(witness)
                    session.commit()
            except Exception as status_exc:
                if session:
                    session.rollback()
                logger.warning('[Celery Task] Failed to persist witness merge failure state: %s', status_exc)
        return {'status': 'error', 'error_type': type(exc).__name__, 'error': str(exc), 'witness_id': witness_id}
    finally:
        if temp_workspace is not None:
            shutil.rmtree(temp_workspace, ignore_errors=True)
        if session:
            try:
                session.close()
            except Exception as exc:
                logger.warning('[Celery Task] Error closing witness merge session: %s', exc)
