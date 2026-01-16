"""
Celery tasks for data synchronization.
Handles database sync (rb9_data mode) via Celery.
CSV sync is manual only - use csv_sync.py for CSV operations.
"""

from datetime import datetime
from src.core.celery_config import celery_app
from src.core.config import config
from src.core.logger import logger
from src.core.sync.sync_handlers import sync_cases, sync_jobs, sync_users
from src.core.sync.config import get_sync_date_range


@celery_app.task(name='src.core.sync.tasks.sync_external_data')
def sync_external_data():
    start_time = datetime.utcnow()
    logger.info(f"[Celery Task] Starting data sync at {start_time}")
    
    data_source = config.SYNC_DATA_SOURCE
    
    # Only handle database sync via Celery - CSV sync is manual only
    if data_source != 'rb9_data':
        logger.warning(f"CSV sync mode ({data_source}) - CSV sync should be run manually from csv_sync.py")
        return {
            'start_time': str(start_time),
            'end_time': str(datetime.utcnow()),
            'duration_seconds': 0,
            'cases': {'error': 'CSV sync is manual only - use csv_sync.py'},
            'jobs': {},
            'users': {},
            'success': False,
            'errors': ['CSV sync must be run manually']
        }
    
    start_date, end_date = get_sync_date_range()
    
    results = {
        'start_time': str(start_time),
        'end_time': None,
        'duration_seconds': None,
        'cases': {},
        'jobs': {},
        'users': {},
        'success': True,
        'errors': []
    }
    
    try:
        logger.info("Starting database sync (external database mode)...")
        logger.info(f"Sync date range: {start_date} to {end_date}")
        
        # Sync Cases
        logger.info("Starting Cases sync...")
        try:
            results['cases'] = sync_cases(start_date=start_date, end_date=end_date)
            logger.info(f"Cases sync completed: {results['cases']}")
        except Exception as e:
            logger.error(f"Cases sync failed: {str(e)}", exc_info=True)
            results['cases'] = {'error': str(e)}
            results['errors'].append(f"Cases: {str(e)}")
            results['success'] = False
        
        # Sync Jobs
        logger.info("Starting Jobs sync...")
        try:
            results['jobs'] = sync_jobs(start_date=start_date, end_date=end_date)
            logger.info(f"Jobs sync completed: {results['jobs']}")
        except Exception as e:
            logger.error(f"Jobs sync failed: {str(e)}", exc_info=True)
            results['jobs'] = {'error': str(e)}
            results['errors'].append(f"Jobs: {str(e)}")
            results['success'] = False
        
        # Sync Users
        logger.info("Starting Users sync...")
        try:
            results['users'] = sync_users(start_date=start_date, end_date=end_date)
            logger.info(f"Users sync completed: {results['users']}")
        except Exception as e:
            logger.error(f"Users sync failed: {str(e)}", exc_info=True)
            results['users'] = {'error': str(e)}
            results['errors'].append(f"Users: {str(e)}")
            results['success'] = False
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        results['end_time'] = str(end_time)
        results['duration_seconds'] = duration
        
        # Log summary
        total_inserted = (
            results['cases'].get('inserted', 0) +
            results['jobs'].get('inserted', 0) +
            results['users'].get('inserted', 0)
        )
        total_updated = (
            results['cases'].get('updated', 0) +
            results['jobs'].get('updated', 0) +
            results['users'].get('updated', 0)
        )
        total_errors = (
            results['cases'].get('errors', 0) +
            results['jobs'].get('errors', 0) +
            results['users'].get('errors', 0)
        )
        
        logger.info(
            f"[Celery Task] Data sync completed in {duration:.2f}s. "
            f"Total: Inserted={total_inserted}, Updated={total_updated}, Errors={total_errors}"
        )
        
        return results
    
    except Exception as e:
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        results['end_time'] = str(end_time)
        results['duration_seconds'] = duration
        results['success'] = False
        results['errors'].append(f"General error: {str(e)}")
        
        logger.error(f"[Celery Task] Data sync failed: {str(e)}", exc_info=True)
        return results
