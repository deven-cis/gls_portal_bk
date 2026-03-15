from fastapi import APIRouter, Depends, Query, Body
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional, Union

from src.auth.utils import get_current_user
from src.core.database import get_db
from src.jobs_tasks.apis import (
    get_cancelled_jobstask_details,
    get_completed_jobstask_details,
    get_mark_as_done_status,
    list_jobstasks_by_case,
    list_pending_jobstasks,
    list_upcoming_jobstasks,
    get_session_start_time,
    start_session,
    end_session,
    cancel_jobstask,
    cancelled_and_completed_jobstasks,
    mark_jobstask_as_done,
    get_calendar_events
)
from src.jobs_tasks.schema import JobsTaskCancelSchema

jobstasks_apis = APIRouter(prefix='/jobs', tags=['jobs'])


@jobstasks_apis.get('/get/{job_no}/cancelled_details', status_code=200)
async def get_cancelled_jobstask_details_route(
    job_no: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    return await get_cancelled_jobstask_details(job_no, current_user, db)


@jobstasks_apis.get('/get/{job_no}/completed_details', status_code=200, response_model=None)
async def get_completed_jobstask_details_route(
    job_no: int,
    download_all: bool = Query(False, description="If true, merge and download all videos"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Union[JSONResponse, FileResponse]:
    return await get_completed_jobstask_details(job_no, download_all, current_user, db)


@jobstasks_apis.get("/get/{job_no}/{case_no}", status_code=200)
async def get_mark_as_done_status_route(
    job_no: int,
    case_no: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    return await get_mark_as_done_status(job_no, case_no, current_user, db)


@jobstasks_apis.get('/list_by_case')
async def list_jobstasks_by_case_route(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await list_jobstasks_by_case(current_user, db)


@jobstasks_apis.get('/pending/')
async def list_pending_jobstasks_route(
    page: Optional[int] = Query(None, ge=1, description="Page number (starts from 1)"),
    page_size: Optional[int] = Query(None, ge=1, le=100, description="Number of items per page"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    return await list_pending_jobstasks(page, page_size, current_user, db)


@jobstasks_apis.get('/upcoming/')
async def list_upcoming_jobstasks_route(
    page: Optional[int] = Query(None, ge=1, description="Page number (starts from 1)"),
    page_size: Optional[int] = Query(None, ge=1, le=100, description="Number of items per page"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    return await list_upcoming_jobstasks(page, page_size, current_user, db)


@jobstasks_apis.get('/get/{job_no}/session_start_time/', status_code=200)
async def get_session_start_time_route(
    job_no: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    return await get_session_start_time(job_no, current_user, db)


@jobstasks_apis.post('/{job_no}/session/start', status_code=200)
async def start_session_route(
    job_no: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    return await start_session(job_no, current_user, db)


@jobstasks_apis.post('/{job_no}/session/end', status_code=200)
async def end_session_route(
    job_no: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    return await end_session(job_no, current_user, db)


@jobstasks_apis.post('/{job_no}/cancel', status_code=200)
async def cancel_jobstask_route(
    job_no: int,
    payload: JobsTaskCancelSchema,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    return await cancel_jobstask(job_no, payload, current_user, db)


@jobstasks_apis.get('/cancelled_and_completed_jobs/{type}')
async def cancelled_and_completed_jobstasks_route(
    type: str,
    adminMode: Optional[bool] = Query(False, description="Set to true to view all records (admin mode)"),
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(5, ge=1, le=100, description="Number of items per page"),
    job_no: Optional[Union[int, str]] = Query(None),
    witness_name: Optional[str] = Query(None),
    case_name: Optional[str] = Query(None),
    case_number: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    return await cancelled_and_completed_jobstasks(
        type, adminMode, start_date, end_date, page, page_size, current_user, db,
        job_no=job_no, witness_name=witness_name, case_name=case_name, case_number=case_number
    )


@jobstasks_apis.patch("/{job_no}/mark_as_done/{type}", status_code=200)
async def mark_jobstask_as_done_route(
    job_no: int,
    type: str,
    body: dict = Body(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    return await mark_jobstask_as_done(job_no, type, body, current_user, db)


@jobstasks_apis.get('/calendar/events', status_code=200)
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


