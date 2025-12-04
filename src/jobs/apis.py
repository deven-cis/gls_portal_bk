from typing import List
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import joinedload

from src.auth.utils import get_current_user
from src.jobs.models import Jobs
from src.core.logger import logger
from src.cases.models import Cases
from src.core.database import db
from src.core.context import get_context

async def list_jobs(
    current_user: dict = Depends(get_current_user),
) -> List[Jobs]:
    """
    Return all jobs for the current user.
    """
    return Jobs.fetch_records({"entered_by": current_user.get("id")})


async def list_jobs_by_case(
    current_user: dict = Depends(get_current_user),
) -> List[Jobs]:
    """
    Return jobs for a specific case that belong to the current user.
    """
    try:
        user_entered_by = get_context('entered_by')
        jobs = (
            db.query(Jobs)
            .join(Cases, Jobs.case_no == Cases.case_no)
            .options(joinedload(Jobs.case))
            .filter(Cases.entered_by == user_entered_by)
            .all()
        )
        return jobs

    except Exception as e:
        logger.error(f"Error fetching jobs by case: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Unable to fetch jobs for the requested case',
        )


async def list_pending_jobs(
    current_user: dict = Depends(get_current_user),
) -> List[Jobs]:
    """
    Return only pending jobs (today's jobs in progress or waiting to start).
    Status: session_not_started or session_in_progress
    Exclude: cancelled jobs
    """
    try:
        user_entered_by = get_context('entered_by')
        today = datetime.now().date()
        
        jobs = (
            db.query(Jobs)
            .join(Cases, Jobs.case_no == Cases.case_no)
            .options(joinedload(Jobs.case))
            .filter(Cases.entered_by == user_entered_by)
            .filter(Jobs.job_date >= datetime.combine(today, datetime.min.time()))
            .filter(Jobs.job_date < datetime.combine(today + timedelta(days=1), datetime.min.time()))
            .filter(Jobs.computed_status.in_(["session_not_started", "session_in_progress"]))
            .filter(Jobs.computed_status != "cancelled")
            .all()
        )
        logger.info(f"Found {len(jobs)} pending jobs for user {user_entered_by}")
        return jobs

    except Exception as e:
        logger.error(f"Error fetching pending jobs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Unable to fetch pending jobs',
        )


async def list_upcoming_jobs(
    current_user: dict = Depends(get_current_user),
) -> List[Jobs]:
    """
    Return only upcoming jobs (tomorrow and beyond).
    Status: upcoming
    """
    try:
        user_entered_by = get_context('entered_by')
        tomorrow = (datetime.now().date() + timedelta(days=1))
        
        jobs = (
            db.query(Jobs)
            .join(Cases, Jobs.case_no == Cases.case_no)
            .options(joinedload(Jobs.case))
            .filter(Cases.entered_by == user_entered_by)
            .filter(Jobs.job_date >= datetime.combine(tomorrow, datetime.min.time()))
            .all()
        )
        logger.info(f"Found {len(jobs)} upcoming jobs for user {user_entered_by}")
        return jobs

    except Exception as e:
        logger.error(f"Error fetching upcoming jobs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Unable to fetch upcoming jobs',
        )
    
