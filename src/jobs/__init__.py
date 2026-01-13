from fastapi import APIRouter, Depends, Query, Body
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional

from src.auth.utils import get_current_user
from src.core.database import get_db
from src.jobs.apis import (
    get_cancelled_job_details,
    get_completed_job_details,
    get_mark_as_done_status,
    list_jobs,
    list_jobs_by_case,
    list_pending_jobs,
    list_upcoming_jobs,
    get_session_start_time,
    start_session,
    end_session,
    cancel_job,
    cancelled_and_completed_jobs,
    mark_job_as_done,
    get_calendar_events
)
from src.jobs.schema import CancelJobSchema

jobs_apis = APIRouter(prefix='/jobs', tags=['jobs'])


@jobs_apis.get('/get/{job_no}/cancelled_details', status_code=200)
async def get_cancelled_job_details_route(
    job_no: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    return await get_cancelled_job_details(job_no, current_user, db)


@jobs_apis.get('/get/{job_no}/completed_details', status_code=200, response_model=None)
async def get_completed_job_details_route(
    job_no: int,
    download_all: bool = Query(False, description="If true, merge and download all videos"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse | FileResponse:
    return await get_completed_job_details(job_no, download_all, current_user, db)


@jobs_apis.get("/get/{job_no}/{case_no}", status_code=200)
async def get_mark_as_done_status_route(
    job_no: int,
    case_no: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    return await get_mark_as_done_status(job_no, case_no, current_user, db)


@jobs_apis.get('/list')
async def list_jobs_route(
    current_user: dict = Depends(get_current_user),
):
    return await list_jobs(current_user)


@jobs_apis.get('/list_by_case')
async def list_jobs_by_case_route(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await list_jobs_by_case(current_user, db)


@jobs_apis.get('/pending/')
async def list_pending_jobs_route(
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    return await list_pending_jobs(page, page_size, current_user, db)


@jobs_apis.get('/upcoming/')
async def list_upcoming_jobs_route(
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    return await list_upcoming_jobs(page, page_size, current_user, db)


@jobs_apis.get('/get/{job_no}/session_start_time/', status_code=200)
async def get_session_start_time_route(
    job_no: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    return await get_session_start_time(job_no, current_user, db)


@jobs_apis.post('/{job_no}/session/start', status_code=200)
async def start_session_route(
    job_no: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    return await start_session(job_no, current_user, db)


@jobs_apis.post('/{job_no}/session/end', status_code=200)
async def end_session_route(
    job_no: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    return await end_session(job_no, current_user, db)


@jobs_apis.post('/{job_no}/cancel', status_code=200)
async def cancel_job_route(
    job_no: int,
    payload: CancelJobSchema,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    return await cancel_job(job_no, payload, current_user, db)


@jobs_apis.get('/cancelled_and_completed_jobs/{type}')
async def cancelled_and_completed_jobs_route(
    type: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    return await cancelled_and_completed_jobs(type, start_date, end_date, page, page_size, current_user, db)


@jobs_apis.patch("/{job_no}/mark_as_done/{type}", status_code=200)
async def mark_job_as_done_route(
    job_no: int,
    type: str,
    body: dict = Body(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    return await mark_job_as_done(job_no, type, body, current_user, db)


@jobs_apis.get('/calendar/events', status_code=200)
async def get_calendar_events_route(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    day: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    return await get_calendar_events(year, month, day, start_date, end_date, current_user, db)

