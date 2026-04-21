from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue
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
    broker_connection_max_retries=5,
    broker_pool_limit=10,
    broker_transport_options={
        'visibility_timeout': 28800,
    },
    result_backend_transport_options={
        'visibility_timeout': 28800,
    },
    beat_schedule_filename='celerybeat-schedule',
    # Keep heavy merge tasks from piling up inside one worker process.
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=28800,
    task_soft_time_limit=27000,
    task_track_started=True,
    result_expires=3600,
    result_persistent=False,
)

celery_app.conf.task_queues = (
    Queue(
        'default',
        exchange=Exchange('default', type='direct'),
        routing_key='default',
    ),
    Queue(
        'merge_queue',
        exchange=Exchange('merge', type='direct'),
        routing_key='video.merge',
    ),
    Queue(
        'cleanup',
        exchange=Exchange('cleanup', type='direct'),
        routing_key='cleanup',
    ),
)

celery_app.conf.task_routes = {
    'src.witnesses.tasks.generate_witness_complete_video_task': {
        'queue': 'merge_queue',
        'routing_key': 'video.merge',
        'rate_limit': '6/m',
    },
    'src.uploaded_videos.tasks.cleanup_expired_uploaded_videos_task': {
        'queue': 'cleanup',
        'routing_key': 'cleanup',
        'rate_limit': '6/h',
    },
    'src.core.sync.tasks.sync_external_data': {
        'queue': 'default',
        'routing_key': 'default',
        'rate_limit': '1/m',
    },
    'src.jobs.tasks.update_job_statuses': {
        'queue': 'default',
        'routing_key': 'default',
        'rate_limit': '2/m',
    },
}

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
            'queue': 'cleanup',
        },
    }
}

logger = logging.getLogger('celery')
logger.setLevel(logging.INFO)
