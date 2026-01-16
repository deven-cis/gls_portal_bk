web: uvicorn src.core.main:app --host 0.0.0.0 --port 8000
worker: celery -A src.core.celery_config worker -l info --include=src.jobs.tasks,src.core.sync.tasks
beat: celery -A src.core.celery_config beat -l info