from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from src.auth.utils import get_current_user
from src.core.database import get_db
from src.billings.apis import get_billing_by_job, create_billing, update_billing, delete_billing

billings_router = APIRouter(prefix="/billings", tags=["billings"])


@billings_router.get("/get/{job_no}", status_code=200)
async def get_billing_by_job_endpoint(
    job_no: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    return await get_billing_by_job(job_no, db)


@billings_router.post("/create", status_code=201)
async def create_billing_endpoint(
    job_no: int = Form(...),
    cancel_en_route: bool = Form(False),
    cancel_setup: bool = Form(False),
    billing_notes: Optional[str] = Form(None),
    videographer_hours_present: Optional[str] = Form(None),
    file_hours_length: Optional[str] = Form(None),
    files: List[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    return await create_billing(
        job_no=job_no,
        cancel_en_route=cancel_en_route,
        cancel_setup=cancel_setup,
        billing_notes=billing_notes,
        videographer_hours_present=videographer_hours_present,
        file_hours_length=file_hours_length,
        files=files,
        db=db
    )


@billings_router.put("/update/{billing_id}", status_code=200)
async def update_billing_endpoint(
    billing_id: int,
    request: Request,
    job_no: Optional[int] = Form(None),
    cancel_en_route: Optional[str] = Form(None),
    cancel_setup: Optional[str] = Form(None),
    billing_notes: Optional[str] = Form(None),
    videographer_hours_present: Optional[str] = Form(None),
    file_hours_length: Optional[str] = Form(None),
    files: List[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    return await update_billing(
        billing_id=billing_id,
        request=request,
        job_no=job_no,
        cancel_en_route=cancel_en_route,
        cancel_setup=cancel_setup,
        billing_notes=billing_notes,
        videographer_hours_present=videographer_hours_present,
        file_hours_length=file_hours_length,
        files=files,
        db=db
    )


@billings_router.delete("/delete/{billing_id}", status_code=200)
async def delete_billing_endpoint(
    billing_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    return await delete_billing(billing_id, db)

