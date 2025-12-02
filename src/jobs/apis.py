from typing import List

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import joinedload

from src.auth.utils import get_current_user
from src.jobs.models import Jobs
from src.core.logger import logger
from src.users.models import Users
from src.cases.models import Cases
from src.core.database import db


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
    results = []
    try:
        user_info = Users.get(current_user.get("id"))
        logger.info(f"User info retrieved for user {user_info.id}")
        
        # Get cases for the current user
        cases = db.query(Cases).filter(Cases.entered_by == user_info.entered_by).all()
        logger.info(f"Found {len(cases)} cases for user {user_info.entered_by}")
        
        # Get all jobs for these cases with case details eager loaded
        case_nos = [case.case_no for case in cases]
        if case_nos:
            jobs = (
                db.query(Jobs)
                .options(joinedload(Jobs.case))
                .filter(Jobs.case_no.in_(case_nos))
                .all()
            )
            logger.info(f"Found {len(jobs)} jobs for these cases")
            results.extend(jobs)

        return results

    except Exception as e:
        logger.error(f"Error fetching jobs by case: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Unable to fetch jobs for the requested case',
        )