#!/usr/bin/env python3
"""
Manual task runner for development.
Runs Celery tasks directly (synchronously) with full logging visible.
"""

import sys
from datetime import datetime
from src.core.logger import logger
from src.core.sync.rb9_to_newgls_synchronization_service import Rb9ToNewGlsSynchronizationService
from src.jobs.tasks import update_job_statuses

def run_sync_external_data():
    """Run sync_external_data task logic directly (without Celery binding)."""
    logger.info("=" * 80)
    logger.info("MANUAL EXECUTION: Starting sync_external_data")
    logger.info("=" * 80)
    
    try:
        start_time = datetime.utcnow()
        logger.info(
            f"[Manual Execution] Starting data sync at {start_time}. "
            f"No timeout limits - task will run until completion."
        )
        
        results = {
            'start_time': str(start_time),
            'end_time': None,
            'duration_seconds': None,
            'success': True,
            'errors': []
        }
        
        logger.info("Starting database sync from rb9_db to new_gls_db...")
        
        # Stage 2: rb9_db → new_gls_db
        logger.info("=" * 60)
        logger.info("STAGE 2: Syncing rb9_db → new_gls_db (ALL DATA)")
        logger.info("=" * 60)
        
        try:
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
            
        except Exception as stage1_error:
            logger.error(f"Stage 1 sync failed: {str(stage1_error)}", exc_info=True)
            results['stage1'] = {'error': str(stage1_error)}
            results['success'] = False
            results['errors'].append(f"Stage 1 error: {str(stage1_error)}")
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        results['end_time'] = str(end_time)
        results['duration_seconds'] = duration
        
        stage1_inserted = results.get('stage1', {}).get('total_inserted', 0)
        stage1_updated = results.get('stage1', {}).get('total_updated', 0)
        stage1_errors = results.get('stage1', {}).get('total_errors', 0)
        stage1_emails = results.get('stage1', {}).get('total_emails_sent', 0)
        
        total_inserted = stage1_inserted
        total_updated = stage1_updated
        total_errors = stage1_errors
        total_emails = stage1_emails
        
        logger.info(
            f"[Manual Execution] Data sync completed in {duration:.2f}s. "
            f"Stage 1: Inserted={stage1_inserted}, Updated={stage1_updated}, Errors={stage1_errors}, EmailsSent={stage1_emails}. "
            f"Total: Inserted={total_inserted}, Updated={total_updated}, Errors={total_errors}, EmailsSent={total_emails}"
        )
        
        logger.info("=" * 80)
        logger.info("MANUAL EXECUTION: sync_external_data completed")
        logger.info(f"Result: {results}")
        logger.info("=" * 80)
        
        return results
        
    except Exception as e:
        logger.error(f"MANUAL EXECUTION: sync_external_data failed: {str(e)}", exc_info=True)
        raise

def run_update_job_statuses():
    """Run update_job_statuses task directly."""
    logger.info("=" * 80)
    logger.info("MANUAL EXECUTION: Starting update_job_statuses")
    logger.info("=" * 80)
    
    try:
        # Call the function directly (not as Celery task)
        result = update_job_statuses()
        logger.info("=" * 80)
        logger.info("MANUAL EXECUTION: update_job_statuses completed")
        logger.info(f"Result: {result}")
        logger.info("=" * 80)
        return result
    except Exception as e:
        logger.error(f"MANUAL EXECUTION: update_job_statuses failed: {str(e)}", exc_info=True)
        raise

def run_both_in_sequence():
    """Run sync first, then update_job_statuses."""
    logger.info("=" * 80)
    logger.info("MANUAL EXECUTION: Running both tasks in sequence")
    logger.info("=" * 80)
    
    # Run sync first
    sync_result = run_sync_external_data()
    
    # Then run update_job_statuses
    update_result = run_update_job_statuses()
    
    logger.info("=" * 80)
    logger.info("MANUAL EXECUTION: Both tasks completed")
    logger.info(f"Sync Result: {sync_result}")
    logger.info(f"Update Result: {update_result}")
    logger.info("=" * 80)
    
    return {
        'sync': sync_result,
        'update': update_result
    }

if __name__ == "__main__":
    if len(sys.argv) > 1:
        task_name = sys.argv[1].lower()
        
        if task_name == "sync":
            run_sync_external_data()
        elif task_name == "update":
            run_update_job_statuses()
        elif task_name == "both":
            run_both_in_sequence()
        else:
            print("Usage: python run_tasks_manual.py [sync|update|both]")
            print("  sync   - Run sync_external_data only")
            print("  update - Run update_job_statuses only")
            print("  both   - Run sync first, then update_job_statuses")
            sys.exit(1)
    else:
        # Default: run both in sequence
        run_both_in_sequence()

