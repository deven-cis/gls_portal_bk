from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError, DatabaseError, OperationalError
from src.core.celery_config import celery_app
from src.core.database import SessionLocal
from src.core.timezone_utils import get_timezone_now
from src.jobs.models import Jobs, JobStatusEnum
from src.core.logger import logger


@celery_app.task(name='src.jobs.tasks.update_job_statuses')
def update_job_statuses():

    start_time = get_timezone_now()  # Use timezone based on app environment
    today = start_time.date()  # Get today's date for comparison (job_date is Date type)
    session = None
    
    try:
        logger.info(f"[Celery Task] Starting job status update at {start_time} (date: {today})")
        
        session = SessionLocal()
        
        # Check for jobs with empty or None computed_status
        jobs_count = session.query(Jobs).filter(
            Jobs.job_date <= today,
            (Jobs.computed_status == '') | (Jobs.computed_status.is_(None))
        ).count()
        
        if jobs_count == 0:
            logger.info(f"[Celery Task] No jobs found with job_date <= {today} and empty/None computed_status")
            return {
                "status": "success",
                "updated_count": 0,
                "duration_seconds": 0,
                "start_time": str(start_time),
                "end_time": str(get_timezone_now())
            }
        
        logger.info(f"[Celery Task] Found {jobs_count} job(s) with job_date <= {today} and empty/None computed_status to update")
        
        updated_count = session.query(Jobs).filter(
            Jobs.job_date <= today,
            (Jobs.computed_status == '') | (Jobs.computed_status.is_(None))
        ).update(
            {Jobs.computed_status: JobStatusEnum.SESSION_NOT_STARTED.value},
            synchronize_session=False
        )
        
        session.commit()
        
        end_time = get_timezone_now()  # Use timezone based on app environment
        duration = (end_time - start_time).total_seconds()
        
        logger.info(
            f"[Celery Task] Successfully updated {updated_count} job(s) to 'Session not started' status "
            f"in {duration:.3f}s"
        )
        
        return {
            "status": "success",
            "updated_count": updated_count,
            "duration_seconds": duration,
            "start_time": str(start_time),
            "end_time": str(end_time)
        }
        
    except OperationalError as e:
        end_time = get_timezone_now()  # Use timezone based on app environment
        duration = (end_time - start_time).total_seconds()
        
        if session:
            try:
                session.rollback()
            except Exception:
                pass
        
        logger.error(
            f"[Celery Task] Database operational error updating job statuses: {str(e)} "
            f"(duration: {duration:.3f}s)",
            exc_info=True
        )
        return {
            "status": "error",
            "error": f"Database operational error: {str(e)}",
            "error_type": "OperationalError",
            "duration_seconds": duration,
            "start_time": str(start_time),
            "end_time": str(end_time)
        }
        
    except DatabaseError as e:
        end_time = get_timezone_now()  # Use timezone based on app environment
        duration = (end_time - start_time).total_seconds()
        
        if session:
            try:
                session.rollback()
            except Exception:
                pass
        
        logger.error(
            f"[Celery Task] Database error updating job statuses: {str(e)} "
            f"(duration: {duration:.3f}s)",
            exc_info=True
        )
        return {
            "status": "error",
            "error": f"Database error: {str(e)}",
            "error_type": "DatabaseError",
            "duration_seconds": duration,
            "start_time": str(start_time),
            "end_time": str(end_time)
        }
        
    except SQLAlchemyError as e:
        end_time = get_timezone_now()  # Use timezone based on app environment
        duration = (end_time - start_time).total_seconds()
        
        if session:
            try:
                session.rollback()
            except Exception:
                pass
        
        logger.error(
            f"[Celery Task] SQLAlchemy error updating job statuses: {str(e)} "
            f"(duration: {duration:.3f}s)",
            exc_info=True
        )
        return {
            "status": "error",
            "error": f"SQLAlchemy error: {str(e)}",
            "error_type": "SQLAlchemyError",
            "duration_seconds": duration,
            "start_time": str(start_time),
            "end_time": str(end_time)
        }
        
    except Exception as e:
        end_time = get_timezone_now()  # Use timezone based on app environment
        duration = (end_time - start_time).total_seconds()
        
        if session:
            try:
                session.rollback()
            except Exception:
                pass
        
        logger.error(
            f"[Celery Task] Unexpected error updating job statuses: {str(e)} "
            f"(duration: {duration:.3f}s)",
            exc_info=True
        )
        return {
            "status": "error",
            "error": f"Unexpected error: {str(e)}",
            "error_type": type(e).__name__,
            "duration_seconds": duration,
            "start_time": str(start_time),
            "end_time": str(end_time)
        }
        
    finally:
        if session:
            try:
                session.close()
            except Exception as e:
                logger.warning(f"[Celery Task] Error closing session: {str(e)}")
