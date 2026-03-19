from sqlalchemy.exc import SQLAlchemyError, DatabaseError, OperationalError

from src.core.celery_config import celery_app
from src.core.database import SessionLocal
from src.core.logger import logger
from src.core.timezone_utils import get_timezone_now
from src.uploaded_videos.services import cleanup_expired_uploaded_videos


@celery_app.task(name='src.uploaded_videos.tasks.cleanup_expired_uploaded_videos_task')
def cleanup_expired_uploaded_videos_task():
    start_time = get_timezone_now()
    session = None

    try:
        logger.info("[Celery Task] Starting expired uploaded video cleanup at %s", start_time)
        session = SessionLocal()

        result = cleanup_expired_uploaded_videos(session, start_time, source="celery")
        session.commit()

        end_time = get_timezone_now()
        duration = (end_time - start_time).total_seconds()

        logger.info(
            "[Celery Task] Expired uploaded video cleanup completed in %.3fs (archived=%s, deleted_files=%s)",
            duration,
            result["archived_uploads"],
            result["deleted_files"],
        )
        return {
            "status": "success",
            "archived_uploads": result["archived_uploads"],
            "deleted_files": result["deleted_files"],
            "duration_seconds": duration,
            "start_time": str(start_time),
            "end_time": str(end_time),
        }

    except OperationalError as e:
        if session:
            session.rollback()
        logger.error("[Celery Task] Database operational error during upload cleanup: %s", str(e), exc_info=True)
        return {"status": "error", "error_type": "OperationalError", "error": str(e)}

    except DatabaseError as e:
        if session:
            session.rollback()
        logger.error("[Celery Task] Database error during upload cleanup: %s", str(e), exc_info=True)
        return {"status": "error", "error_type": "DatabaseError", "error": str(e)}

    except SQLAlchemyError as e:
        if session:
            session.rollback()
        logger.error("[Celery Task] SQLAlchemy error during upload cleanup: %s", str(e), exc_info=True)
        return {"status": "error", "error_type": "SQLAlchemyError", "error": str(e)}

    except Exception as e:
        if session:
            session.rollback()
        logger.error("[Celery Task] Unexpected error during upload cleanup: %s", str(e), exc_info=True)
        return {"status": "error", "error_type": type(e).__name__, "error": str(e)}

    finally:
        if session:
            try:
                session.close()
            except Exception as e:
                logger.warning("[Celery Task] Error closing cleanup session: %s", str(e))
