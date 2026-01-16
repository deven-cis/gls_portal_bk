from celery import Celery
from celery.schedules import crontab
from src.core.config import config
import logging

celery_app = Celery(
    'gls_api',
    broker=config.CELERY_BROKER_URL,
    backend=config.CELERY_RESULT_BACKEND
)

# Auto-discover tasks from all modules
celery_app.autodiscover_tasks(['src.jobs', 'src.core.sync'])

# Explicitly import task modules to ensure they're loaded
try:
    from src.jobs import tasks as jobs_tasks  # noqa: F401
except ImportError:
    pass

try:
    from src.core.sync import tasks as sync_tasks  # noqa: F401
except ImportError:
    pass

# Configure logging
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s',
)

# Beat schedule
celery_app.conf.beat_schedule = {
    # 'update-job-statuses-every-minute': {
    #     'task': 'src.jobs.tasks.update_job_statuses',
    #     'schedule': crontab(minute='*/1'),
    # },
    'sync-external-data-every-15-minutes': {
        'task': 'src.core.sync.tasks.sync_external_data',
        'schedule': crontab(minute='*/1'),
    },
}

# Configure root logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('celery')
logger.setLevel(logging.INFO)