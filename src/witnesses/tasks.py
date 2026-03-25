import asyncio
from pathlib import Path

from sqlalchemy.exc import DatabaseError, OperationalError, SQLAlchemyError

from src.core.celery_config import celery_app
from src.core.database import SessionLocal
from src.core.file_utils import extract_video_metadata
from src.core.logger import logger
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

        output_path = build_witness_merged_video_output_path(witness.id, witness.job_no)
        merge_video_files_ffmpeg(
            [video.file_path for video in videos],
            output_path,
            log_label=f'witness {witness.id} job {witness.job_no}',
        )

        metadata = asyncio.run(extract_video_metadata(str(output_path)))
        completed_at = get_timezone_now()

        witness.merged_video_path = str(output_path)
        witness.merged_video_name = output_path.name
        witness.merged_video_size = metadata.get('file_size') or output_path.stat().st_size
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
            'output_path': str(output_path),
            'merged_video_name': output_path.name,
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
        if session:
            try:
                session.close()
            except Exception as exc:
                logger.warning('[Celery Task] Error closing witness merge session: %s', exc)
