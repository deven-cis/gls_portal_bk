from typing import List, Optional
from fastapi import APIRouter, Query, Form, File, UploadFile

from src.equipment_time.apis import (
    list_equipment_times, get_equipment_time, create_equipment_time,
    update_equipment_time, delete_equipment_time, upload_equipment_time_files
)
from src.equipment_time.schema import (
    EquipmentTimeSchema, EquipmentTimeUpdateSchema
)


equipment_time_router = APIRouter(prefix='/equipment-time', tags=['equipment-time'])


@equipment_time_router.get('', response_model=List[EquipmentTimeSchema])
async def list_equipment_times_route(job_no: Optional[int] = Query(None)):
    return await list_equipment_times(job_no=job_no)


@equipment_time_router.get('/{equipment_time_id}', response_model=EquipmentTimeSchema)
async def get_equipment_time_route(equipment_time_id: int):
    return await get_equipment_time(equipment_time_id)


@equipment_time_router.post('', response_model=EquipmentTimeSchema, status_code=201)
async def create_equipment_time_route(
    job_no: int = Form(...),
    laptop_used: bool = Form(False),
    pip_used: bool = Form(False),
    exhibit_tech: bool = Form(False),
    parking_cost: Optional[str] = Form(None),
    time_after: Optional[str] = Form(None),
    files: List[UploadFile] = File(None),
):
    return await create_equipment_time(
        job_no=job_no,
        laptop_used=laptop_used,
        pip_used=pip_used,
        exhibit_tech=exhibit_tech,
        parking_cost=parking_cost,
        time_after=time_after,
        files=files,
    )


@equipment_time_router.post('/{equipment_time_id}/upload', status_code=201)
async def upload_equipment_time_files_route(
    equipment_time_id: int,
    files: List[UploadFile] = File(...),
):
    return await upload_equipment_time_files(equipment_time_id, files)


@equipment_time_router.put('/{equipment_time_id}', response_model=EquipmentTimeSchema)
async def update_equipment_time_route(
    equipment_time_id: int,
    equipment_time_data: EquipmentTimeUpdateSchema
):
    return await update_equipment_time(equipment_time_id, equipment_time_data)


@equipment_time_router.delete('/{equipment_time_id}', status_code=204)
async def delete_equipment_time_route(equipment_time_id: int):
    return await delete_equipment_time(equipment_time_id)
