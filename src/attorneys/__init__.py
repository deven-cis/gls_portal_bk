from typing import Optional
from fastapi import Depends, UploadFile, File, Form, APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from src.auth.utils import get_current_user
from src.core.database import get_db
from src.attorneys import apis

attorneys_router = APIRouter(prefix='/attorneys', tags=['attorneys'])


@attorneys_router.get('/list/{job_no}', status_code=200)
async def list_attorneys_by_job(
    job_no: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    return await apis.list_attorneys_by_job(job_no, db)


@attorneys_router.post('/create', status_code=201)
async def create_attorney(
    job_no: int = Form(...),
    attorney_name: str = Form(...),
    firm_name: str = Form(...),
    notes: str = Form(...),
    order_details: str = Form(...),
    document: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    return await apis.create_attorney(
        job_no=job_no,
        attorney_name=attorney_name,
        firm_name=firm_name,
        notes=notes,
        order_details=order_details,
        document=document
    )


@attorneys_router.put('/update/{attorney_id}', status_code=200)
async def update_attorney(
    attorney_id: int,
    request: Request,
    attorney_name: Optional[str] = Form(None),
    firm_name: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    order_details: Optional[str] = Form(None),
    document: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    return await apis.update_attorney(
        attorney_id=attorney_id,
        request=request,
        attorney_name=attorney_name,
        firm_name=firm_name,
        notes=notes,
        order_details=order_details,
        document=document
    )


@attorneys_router.delete('/delete/{attorney_id}', status_code=200)
async def delete_attorney(
    attorney_id: int,
    current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    return await apis.delete_attorney(attorney_id)
