from typing import List

from fastapi import Depends, HTTPException, status

from src.auth.utils import get_current_user
from src.jobs.models import Jobs
from src.core.logger import logger
from src.users.models import Users
from src.cases.models import Cases


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
        current_user_all_cases = Cases.fetch_records({"entered_by": user_info.entered_by})
        for case in current_user_all_cases:
            cases_jobs = Jobs.fetch_records({"case_no": case.id})  
            for job in cases_jobs:
                results.append({
                    "case_short_name": case.case_short_name,
                    "case_full_name": case.case_full_name,
                    "case_type": case.case_type,
                    "case_status": case.status,
                    "job_date": job.job_date,
                    "start_time": job.start_time,
                    "end_time": job.end_time,
                    "timezone_no": job.timezone_no,
                    "status": job.status,
                    "case_no": job.case_no,
                    "job_loc_name": job.job_loc_name,
                    "job_loc_address": job.job_loc_address,
                    "job_loc_city": job.job_loc_city,
                    "job_loc_state": job.job_loc_state,
                    "job_loc_zip": job.job_loc_zip,
                    "zoom_meeting_id": job.zoom_meeting_id,
                    "cancel_by": job.cancel_by,
                    "cancel_date": job.cancel_date,
                })
        return results

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Unable to fetch jobs for the requested case',
        ) from exc