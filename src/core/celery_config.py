from celery import Celery
from celery.schedules import crontab
from src.core.config import config
from src.core.timezone_utils import get_default_timezone
import logging

celery_app = Celery(
    'gls_api',
    broker=config.CELERY_BROKER_URL,
    backend=config.CELERY_RESULT_BACKEND
)

celery_app.autodiscover_tasks(['src.jobs', 'src.core.sync', 'src.uploaded_videos', 'src.witnesses'])


celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone=get_default_timezone(),
    enable_utc=False,
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s',
    broker_connection_retry_on_startup=True,
    beat_schedule_filename='celerybeat-schedule',
    # Prevent overlapping task executions
    worker_prefetch_multiplier=1, 
    task_acks_late=True,
    task_reject_on_worker_lost=True,  
)

celery_app.conf.beat_schedule = {
    # 'update-job-statuses-every-day': {
    #     'task': 'src.jobs.tasks.update_job_statuses',
    #     'schedule': crontab(hour=0, minute=0),  
    # },
    # 'sync-external-data-every-day': {
    #     'task': 'src.core.sync.tasks.sync_external_data',
    #     'schedule': crontab(minute='*/2'),
    #     'options': {
    #         'expires': 300, 
    #     },
    # },
    'cleanup-expired-uploaded-videos-every-5-hours': {
        'task': 'src.uploaded_videos.tasks.cleanup_expired_uploaded_videos_task',
        'schedule': crontab(minute=0, hour='*/5'),
        'options': {
            'expires': 7200,
        },
    }
}

logger = logging.getLogger('celery')
logger.setLevel(logging.INFO)
