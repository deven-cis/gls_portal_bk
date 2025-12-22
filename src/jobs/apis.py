from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload

from src.auth.utils import get_current_user
from src.jobs.models import Jobs
from src.core.logger import logger
from src.cases.models import Cases
from src.core.database import get_db
from src.core.context import get_context
from fastapi import APIRouter
from src.jobs.schema import JobSchema
from src.jobs.models import JobStatusEnum

jobs_apis = APIRouter(prefix='/jobs', tags=['jobs'])

@jobs_apis.get('/list')
async def list_jobs(
    current_user: dict = Depends(get_current_user),
) -> List[JobSchema]:
    """
    Return all jobs for the current user.
    """
    return Jobs.fetch_records({"entered_by": current_user.get("id")})


@jobs_apis.get('/list_by_case')
async def list_jobs_by_case(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
) -> List[JobSchema]:
    """
    Return jobs for a specific case that belong to the current user.
    """
    try:
        user_entered_by = get_context('entered_by')
        logger.info(f"Fetching jobs for user {user_entered_by}")
        jobs = (
            db.query(Jobs)
            .join(Cases, Jobs.case_no == Cases.case_no)
            .options(joinedload(Jobs.case))
            .filter(Cases.entered_by == user_entered_by)
            .all()
        )
        return [JobSchema.model_validate(job).model_dump() for job in jobs]

    except Exception as e:
        logger.error(f"Error fetching jobs by case: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Unable to fetch jobs for the requested case',
        )

@jobs_apis.get('/pending/')
async def list_pending_jobs(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
) -> List[JobSchema]:
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
            # .filter(Jobs.session_completed == False)
            # .filter(Jobs.computed_status != "cancelled")
            .all()
        )
        logger.info(f"Found {len(jobs)} pending jobs for user {user_entered_by}")
        return [JobSchema.model_validate(job).model_dump() for job in jobs]

    except Exception as e:
        logger.error(f"Error fetching pending jobs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Unable to fetch pending jobs',
        )

@jobs_apis.get('/upcoming/')
async def list_upcoming_jobs(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
) -> List[JobSchema]:
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
        return [JobSchema.model_validate(job).model_dump() for job in jobs]

    except Exception as e:
        logger.error(f"Error fetching upcoming jobs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Unable to fetch upcoming jobs',
        )

@jobs_apis.get('/get/{job_no}/session_start_time/', status_code=200)
async def get_session_start_time(
    job_no: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    """
    Get a session for a job.
    """
    try:
        logger.info(f"Getting session start time for job_no {job_no}")
        user_entered_by = get_context('entered_by')
        job = (
            db.query(Jobs)
            .join(Cases, Jobs.case_no == Cases.case_no)
            .filter(Cases.is_archived == False)
            .filter(Jobs.job_no == job_no)
            .filter(Jobs.is_archived == False)
            .filter(Cases.entered_by == user_entered_by)
            .first()
        )
        if not job:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Job with job_no {job_no} not found or access denied",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )
        session_start_time_is_on = True if job.actual_session_start_time else False
        if job.computed_status == JobStatusEnum.SESSION_IN_PROGRESS.value:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Session is in progress",
                    "success": True,
                    "status": job.computed_status,
                    "result": job.actual_session_start_time.isoformat() if session_start_time_is_on else {}
                },
                status_code=status.HTTP_200_OK
            )
        if job.computed_status == JobStatusEnum.SESSION_NOT_STARTED.value:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Session is not started",
                    "success": True,
                    "status": job.computed_status,
                    "result": {}
                },  
                status_code=status.HTTP_200_OK
            )
        if job.computed_status == JobStatusEnum.COMPLETED.value:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Session is completed",
                    "success": True,
                    "status": job.computed_status,
                    "result": {}
                },
                status_code=status.HTTP_200_OK
            )
        if job.computed_status == JobStatusEnum.SCHEDULED.value:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Session is scheduled",
                    "success": True,
                    "status": job.computed_status,
                    "result": {}
                },
                status_code=status.HTTP_200_OK
            )


    except Exception as e:
        logger.error(f"Error getting session for job_no {job_no}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Failed to get session",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )




@jobs_apis.post('/{job_no}/session/start', status_code=200)
async def start_session(
    job_no: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    """
    Start a session for a job.
    Sets actual_session_start_time to current time and updates status to session_started.
    """
    try:
        user_entered_by = get_context('entered_by')
        
        # Find the job and verify it belongs to the user
        job = (
            db.query(Jobs)
            .join(Cases, Jobs.case_no == Cases.case_no)
            .filter(Jobs.job_no == job_no)
            .filter(Cases.entered_by == user_entered_by)
            .filter(Jobs.session_completed == False)
            .first()
        )
        
        if not job:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Job with job_no {job_no} not found or access denied",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )
    
        
        # Start the session
        job.actual_session_start_time = datetime.now()
        job.computed_status =  JobStatusEnum.SESSION_IN_PROGRESS.value
        
        db.commit()
        db.refresh(job)
        
        logger.info(f"Session started for job_no {job_no} at {job.actual_session_start_time}")
        
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Session started successfully",
                "success": True,
                "result": {
                    "job_no": job.job_no,
                    "start_time": job.actual_session_start_time.isoformat(),
                    "computed_status": job.computed_status
                }
            },
            status_code=status.HTTP_200_OK
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error starting session for job_no {job_no}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Failed to start session",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@jobs_apis.post('/{job_no}/session/end', status_code=200)
async def end_session(
    job_no: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    """
    End a session for a job.
    Sets actual_session_end_time, calculates duration, and marks session as completed.
    """
    try:
        user_entered_by = get_context('entered_by')
        
        # Find the job and verify it belongs to the user
        job = (
            db.query(Jobs)
            .join(Cases, Jobs.case_no == Cases.case_no)
            .filter(Cases.is_archived == False)
            .filter(Jobs.is_archived == False)
            .filter(Jobs.job_no == job_no)
            .filter(Jobs.computed_status == JobStatusEnum.SESSION_IN_PROGRESS.value)
            .filter(Jobs.actual_session_start_time is not None)
            .filter(Cases.entered_by == user_entered_by)
            .filter(Jobs.session_completed == False)
            .first()
        )
        
        if not job:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Job with job_no {job_no} not found or access denied",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )
       
        
        # End the session
        job.actual_session_end_time = datetime.now()
        
        # Calculate duration
        duration = job.actual_session_end_time - job.actual_session_start_time
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        job.session_duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        job.session_completed = True
        job.computed_status = JobStatusEnum.COMPLETED.value
        
        db.commit()
        db.refresh(job)
        
        logger.info(
            f"Session ended for job_no {job_no}. "
            f"Duration: {job.session_duration}"
        )
        
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Session ended successfully",
                "success": True,
                "result": {}
            },
            status_code=status.HTTP_200_OK
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error ending session for job_no {job_no}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Failed to end session",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


