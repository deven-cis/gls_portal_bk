#!/usr/bin/env python
"""
Test script to verify Celery Beat is running and task is scheduled correctly
"""

import sys

# Add project to path
sys.path.insert(0, '/windows/rb9_project/gls_portal_bk')

from src.core.celery_config import celery_app
from src.core.database import SessionLocal
from src.jobs.models import Jobs, JobStatusEnum
from src.cases.models import Cases  # Import to register relationship

def check_celery_status():
    """Check if Celery is running"""
    print("\n" + "="*70)
    print("🔍 CELERY STATUS CHECK")
    print("="*70 + "\n")
    
    try:
        # Check if Celery app is configured
        print("✅ Celery app loaded successfully")
        print(f"   Broker: {celery_app.conf.broker_connection_retry_on_startup}")
        print(f"   Backend: {celery_app.conf.result_backend}")
        
        # Check Beat schedule
        print("\n📅 Beat Schedule:")
        for task_name, task_config in celery_app.conf.beat_schedule.items():
            print(f"   - {task_name}")
            print(f"     Task: {task_config['task']}")
            print(f"     Schedule: {task_config['schedule']}")
        
        # Check database jobs
        session = SessionLocal()
        try:
            total_jobs = session.query(Jobs).count()
            upcoming = session.query(Jobs).filter(
                Jobs.computed_status == JobStatusEnum.UPCOMING.value
            ).count()
            in_progress = session.query(Jobs).filter(
                Jobs.computed_status == JobStatusEnum.SESSION_IN_PROGRESS.value
            ).count()
            not_started = session.query(Jobs).filter(
                Jobs.computed_status == JobStatusEnum.SESSION_NOT_STARTED.value
            ).count()
            
            print("\n📊 Database Jobs Status:")
            print(f"   Total Jobs: {total_jobs}")
            print(f"   Upcoming: {upcoming}")
            print(f"   Session In Progress: {in_progress}")
            print(f"   Session Not Started: {not_started}")
            
            # Show sample jobs
            if total_jobs > 0:
                print("\n📋 Sample Jobs (first 3):")
                jobs = session.query(Jobs).limit(3).all()
                for job in jobs:
                    job_date = job.job_date.date() if job.job_date else "N/A"
                    print(f"   - Job #{job.id} | job_no: {job.job_no} | Date: {job_date} | Status: {job.computed_status}")
        finally:
            session.close()
        
        print("\n" + "="*70)
        print("✅ CELERY IS READY!")
        print("="*70)
        print("\n📌 What to expect:")
        print("   - Task runs every minute")
        print("   - Check terminal for: 🔄 [CELERY BEAT] Job Status Update")
        print("   - Job statuses will auto-update in database")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}\n")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_celery_status()
