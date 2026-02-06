from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from src.auth.utils import get_current_user
from src.core.database import get_db
from src.equipment_time.apis import get_equipment_time_by_job, create_equipment_time, update_equipment_time, delete_equipment_time

equipment_time_router = APIRouter(prefix="/equipment-time", tags=["equipment-time"])


@equipment_time_router.get("/get/{job_no}", status_code=200)
async def get_equipment_time_by_job_endpoint(
    job_no: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:

    return await get_equipment_time_by_job(job_no, db)


@equipment_time_router.post("/create", status_code=201)
async def create_equipment_time_endpoint(
    job_no: int = Form(...),
    laptop_used: bool = Form(False),
    pip_used: bool = Form(False),
    exhibit_tech: bool = Form(False),
    parking_cost: Optional[str] = Form(None),
    time_after: Optional[str] = Form(None),
    files: List[UploadFile] = File(None),
    camera_captured_file: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:

    return await create_equipment_time(
        job_no=job_no,
        laptop_used=laptop_used,
        pip_used=pip_used,
        exhibit_tech=exhibit_tech,
        parking_cost=parking_cost,
        time_after=time_after,
        files=files,
        camera_captured_file=camera_captured_file,
        db=db
    )


@equipment_time_router.put("/update/{equipment_time_id}", status_code=200)
async def update_equipment_time_endpoint(
    equipment_time_id: int,
    request: Request,
    laptop_used: Optional[str] = Form(None),
    pip_used: Optional[str] = Form(None),
    exhibit_tech: Optional[str] = Form(None),
    parking_cost: Optional[str] = Form(None),
    time_after: Optional[str] = Form(None),
    files: List[UploadFile] = File(None),
    camera_captured_file: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:

    return await update_equipment_time(
        equipment_time_id=equipment_time_id,
        request=request,
        laptop_used=laptop_used,
        pip_used=pip_used,
        exhibit_tech=exhibit_tech,
        parking_cost=parking_cost,
        time_after=time_after,
        files=files,
        db=db,
        camera_captured_file=camera_captured_file
    )


@equipment_time_router.delete("/delete/{equipment_time_id}", status_code=200)
async def delete_equipment_time_endpoint(
    equipment_time_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:

    return await delete_equipment_time(equipment_time_id, db)

