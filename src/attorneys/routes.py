from typing import List, Optional
from fastapi import APIRouter, Query, Form, File, UploadFile

from src.attorneys.apis import (
    list_attorneys,
    get_attorney,
    create_attorney,
    update_attorney,
    delete_attorney,
    upload_attorney_file,
)
from src.attorneys.schema import AttorneySchema


attorneys_router = APIRouter(prefix='/attorneys', tags=['attorneys'])


@attorneys_router.get('', response_model=List[AttorneySchema])
async def list_attorneys_route(
    job_no: Optional[int] = Query(None, description="Filter by job number"),
):
    return await list_attorneys(job_no=job_no)


@attorneys_router.get('/{attorney_id}', response_model=AttorneySchema)
async def get_attorney_route(attorney_id: int):
    return await get_attorney(attorney_id)


@attorneys_router.post('', response_model=AttorneySchema, status_code=201)
async def create_attorney_route(
    job_no: int = Form(...),
    attorney_name: str = Form(...),
    firm_name: str = Form(...),
    notes: str = Form(...),
    order_details: str = Form(...),
    file: Optional[UploadFile] = File(None),
):
    return await create_attorney(
        job_no=job_no,
        attorney_name=attorney_name,
        firm_name=firm_name,
        notes=notes,
        order_details=order_details,
        file=file,
    )


@attorneys_router.post('/{attorney_id}/upload', response_model=AttorneySchema)
async def upload_attorney_file_route(
    attorney_id: int,
    file: UploadFile = File(...),
):
    return await upload_attorney_file(attorney_id, file)


@attorneys_router.put('/{attorney_id}', response_model=AttorneySchema)
async def update_attorney_route(
    attorney_id: int,
    attorney_name: Optional[str] = Form(None),
    firm_name: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    order_details: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    return await update_attorney(
        attorney_id=attorney_id,
        attorney_name=attorney_name,
        firm_name=firm_name,
        notes=notes,
        order_details=order_details,
        file=file,
    )


@attorneys_router.delete('/{attorney_id}', status_code=204)
async def delete_attorney_route(attorney_id: int):
    return await delete_attorney(attorney_id)
