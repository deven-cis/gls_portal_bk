
from datetime import datetime
from src.core.celery_config import celery_app
from src.core.config import config
from src.core.logger import logger
from src.core.sync.config import get_sync_date_range
from src.core.sync.rb9_to_newgls_synchronization_service import Rb9ToNewGlsSynchronizationService


@celery_app.task(name='src.core.sync.tasks.sync_external_data', bind=True)
def sync_external_data(self):
    """
    Sync data from rb9_db to new_gls_db.
    No timeout limits - task will run until completion.
    Task state is updated periodically to show progress.
    """
    start_time = datetime.utcnow()
    logger.info(
        f"[Celery Task] Starting data sync at {start_time}. "
        f"No timeout limits - task will run until completion."
    )
    
    # Update task state to show it's running
    self.update_state(
        state='PROGRESS',
        meta={'status': 'Starting sync...', 'start_time': str(start_time)}
    )
    
    results = {
        'start_time': str(start_time),
        'end_time': None,
        'duration_seconds': None,
        'success': True,
        'errors': []
    }
    
    try:
        logger.info("Starting database sync from rb9_db to new_gls_db...")
        
        # Stage 2: rb9_db → new_gls_db
        logger.info("=" * 60)
        logger.info("STAGE 2: Syncing rb9_db → new_gls_db (ALL DATA)")
        logger.info("=" * 60)
        
        try:
            # Update task state - sync in progress
            self.update_state(
                state='PROGRESS',
                meta={'status': 'Syncing data...', 'start_time': str(start_time)}
            )
            start_dt = datetime(2020, 1, 1, 0, 0, 0)
            end_dt = datetime(2026, 2, 19, 23, 59, 59, 999999)
            
            # Sync ALL data - no date restrictions, no limits
            # Uses hybrid approach: pagination + bulk operations for scalability
            stage1_service = Rb9ToNewGlsSynchronizationService()
            stage1_results = stage1_service.synchronize_all_tables(
                start_date=start_dt,  
                end_date=end_dt,    
                limit=None,       
                batch_size=1000,  
                use_bulk_ops=True 
            )
            
            results['stage1'] = stage1_results
            logger.info(f"Stage 1 completed: {stage1_results}")
            
            # Update task state - sync completed
            self.update_state(
                state='PROGRESS',
                meta={
                    'status': 'Sync completed',
                    'inserted': stage1_results.get('total_inserted', 0),
                    'updated': stage1_results.get('total_updated', 0),
                    'errors': stage1_results.get('total_errors', 0)
                }
            )
        except Exception as stage1_error:
            logger.error(f"Stage 1 sync failed: {str(stage1_error)}", exc_info=True)
            results['stage1'] = {'error': str(stage1_error)}
            results['success'] = False
            results['errors'].append(f"Stage 1 error: {str(stage1_error)}")
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        results['end_time'] = str(end_time)
        results['duration_seconds'] = duration
        
        stage1_inserted = stage1_results.get('total_inserted', 0)
        stage1_updated = stage1_results.get('total_updated', 0)
        stage1_errors = stage1_results.get('total_errors', 0)
        stage1_emails = stage1_results.get('total_emails_sent', 0)
        
        total_inserted =  stage1_inserted
        total_updated = stage1_updated
        total_errors = stage1_errors
        total_emails = stage1_emails
        logger.info(
            f"[Celery Task] Data sync completed in {duration:.2f}s. "
            f"Stage 1: Inserted={stage1_inserted}, Updated={stage1_updated}, Errors={stage1_errors}, EmailsSent={stage1_emails}. "
            f"Total: Inserted={total_inserted}, Updated={total_updated}, Errors={total_errors}, EmailsSent={total_emails}"
        )
        
        return results
    
    except Exception as e:
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        results['end_time'] = str(end_time)
        results['duration_seconds'] = duration
        results['success'] = False
        results['errors'].append(f"General error: {str(e)}")
        
        # Update task state - sync failed
        self.update_state(
            state='FAILURE',
            meta={
                'status': 'Sync failed',
                'error': str(e),
                'duration_seconds': duration
            }
        )
        
        logger.error(
            f"[Celery Task] Data sync failed with critical error: {str(e)}. "
            f"Duration: {duration:.2f}s. "
            f"Stopping sync cleanly to prevent data corruption.",
            exc_info=True
        )
        
        # Log final summary even on error
        logger.info(
            f"[Celery Task] Sync stopped cleanly. "
            f"Final stats - Inserted: {results.get('stage1', {}).get('total_inserted', 0)}, "
            f"Updated: {results.get('stage1', {}).get('total_updated', 0)}, "
            f"Errors: {results.get('stage1', {}).get('total_errors', 0)}"
        )
        
        return results
