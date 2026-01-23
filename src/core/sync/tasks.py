
from datetime import datetime
from src.core.celery_config import celery_app
from src.core.config import config
from src.core.logger import logger
from src.core.sync.config import get_sync_date_range
from src.core.sync.external_to_rb9_synchronization_service import ExternalToRb9SynchronizationService
from src.core.sync.rb9_to_newgls_synchronization_service import Rb9ToNewGlsSynchronizationService


@celery_app.task(name='src.core.sync.tasks.sync_external_data')
def sync_external_data():
    start_time = datetime.utcnow()
    logger.info(f"[Celery Task] Starting data sync at {start_time}")
    
    results = {
        'start_time': str(start_time),
        'end_time': None,
        'duration_seconds': None,
        'success': True,
        'errors': []
    }
    
    try:
        logger.info("Starting two-stage database sync...")
        
        # Stage 1: External DB → rb9_db
        logger.info("=" * 60)
        logger.info("STAGE 1: Syncing External DB → rb9_db")
        logger.info("=" * 60)
        
        # For testing: use static date and limit to 2 records
        test_start_date = datetime(2009, 10, 5, 0, 0, 0)
        test_end_date = datetime(2009, 10, 5, 23, 59, 59, 999999)
        test_limit = 3  # Limit to 2 records for testing
        
        stage1_service = ExternalToRb9SynchronizationService()
        stage1_results = stage1_service.sync_all(
            start_date=test_start_date,
            end_date=test_end_date,
            limit=test_limit
        )
        
        results['stage1'] = stage1_results
        logger.info(f"Stage 1 completed: {stage1_results}")
        
        # Stage 2: rb9_db → new_gls_db
        logger.info("=" * 60)
        logger.info("STAGE 2: Syncing rb9_db → new_gls_db")
        logger.info("=" * 60)
        
        try:
            # For testing: use same date range and limit as Stage 1
            stage2_service = Rb9ToNewGlsSynchronizationService()
            stage2_results = stage2_service.synchronize_all_tables(
                start_date=test_start_date,
                end_date=test_end_date,
                limit=test_limit
            )
            
            results['stage2'] = stage2_results
            logger.info(f"Stage 2 completed: {stage2_results}")
        except Exception as stage2_error:
            logger.error(f"Stage 2 sync failed: {str(stage2_error)}", exc_info=True)
            results['stage2'] = {'error': str(stage2_error)}
            results['success'] = False
            results['errors'].append(f"Stage 2 error: {str(stage2_error)}")
        
        
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        results['end_time'] = str(end_time)
        results['duration_seconds'] = duration
        
        # Log summary (include Stage 1 and Stage 2)
        stage1_inserted = stage1_results.get('total_inserted', 0)
        stage1_updated = stage1_results.get('total_updated', 0)
        stage1_errors = stage1_results.get('total_errors', 0)
        
        stage2_inserted = stage2_results.get('total_inserted', 0)
        stage2_updated = stage2_results.get('total_updated', 0)
        stage2_errors = stage2_results.get('total_errors', 0)
        stage2_emails = stage2_results.get('total_emails_sent', 0)
        
        total_inserted = stage1_inserted + stage2_inserted
        total_updated = stage1_updated + stage2_updated
        total_errors = stage1_errors + stage2_errors
        
        logger.info(
            f"[Celery Task] Data sync completed in {duration:.2f}s. "
            f"Stage 1: Inserted={stage1_inserted}, Updated={stage1_updated}, Errors={stage1_errors}. "
            f"Stage 2: Inserted={stage2_inserted}, Updated={stage2_updated}, Errors={stage2_errors}, EmailsSent={stage2_emails}. "
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
