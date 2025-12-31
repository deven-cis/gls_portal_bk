from datetime import datetime
from src.core.celery_config import celery_app
from src.core.database import SessionLocal
from src.jobs.models import Jobs
from src.core.logger import logger
from src.attorneys.models import Attorneys
from src.billings.models import Billings
from src.additional_documents.models import AdditionalDocuments
from src.equipment_time.models import EquipmentTime
from src.witnesses.models import Witnesses
from src.witness_videos.models import WitnessVideos
from src.job_assignment.models import JobAssignment

@celery_app.task(name='src.jobs.tasks.update_job_statuses')
def update_job_statuses():
    """
    Celery task that runs every minute to automatically shift jobs from 
    upcoming → pending when job_date is today.
    
    Status transitions:
    - UPCOMING → SESSION_NOT_STARTED (if today and before start_time)
    - UPCOMING → SESSION_IN_PROGRESS (if today and after start_time)
    """
    session = SessionLocal()
    try:
        now = datetime.now()
        today = now.date()
        current_time = now.time()
        
        # Print to console (visible in terminal)
        print(f"\n{'='*70}")
        print(f"🔄 [CELERY BEAT] Job Status Update - {now}")
        print(f"{'='*70}")
        logger.info(f"[Celery Task] Starting job status update at {now}")
        
        # Find all upcoming jobs
        upcoming_jobs = session.query(Jobs).filter(
            Jobs.computed_status == "upcoming"
        ).all()
        
        print(f"📊 Found {len(upcoming_jobs)} upcoming jobs to check\n")
        
        updated_count = 0
        
        for job in upcoming_jobs:
            job_date = job.job_date.date() if job.job_date else None
            
            # Check if job is today
            if job_date == today:
                # Job is today - update status based on start_time
                if current_time >= job.start_time:
                    job.computed_status = "session_in_progress"
                    print(f"  ✅ Job #{job.id} (job_no: {job.job_no}) → SESSION_IN_PROGRESS")
                    logger.info(f"Job {job.id} transitioned to SESSION_IN_PROGRESS")
                else:
                    job.computed_status = "session_not_started"
                    time_until = (datetime.combine(today, job.start_time) - datetime.combine(today, current_time)).total_seconds() / 60
                    print(f"  ⏳ Job #{job.id} (job_no: {job.job_no}) → SESSION_NOT_STARTED (starts in {int(time_until)} minutes)")
                    logger.info(f"Job {job.id} transitioned to SESSION_NOT_STARTED")
                
                updated_count += 1
        
        session.commit()
        
        print(f"\n✨ Successfully updated {updated_count} jobs")
        print(f"{'='*70}\n")
        logger.info(f"[Celery Task] Updated {updated_count} jobs")
        
        return {
            "status": "success",
            "updated_count": updated_count,
            "timestamp": str(now)
        }
        
    except Exception as e:
        
        session.rollback()
        print(f"\n❌ ERROR: {str(e)}\n")
        logger.error(f"[Celery Task] Error updating job statuses: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        session.close()
