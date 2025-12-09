from typing import List, Optional
from fastapi import APIRouter, Query, Form, File, UploadFile

from src.billings.apis import (
    list_billings, get_billing, create_billing, update_billing,
    delete_billing, upload_billing_files
)
from src.billings.schema import BillingSchema, BillingUpdateSchema


billings_router = APIRouter(prefix='/billings', tags=['billings'])


@billings_router.get('', response_model=List[BillingSchema])
async def list_billings_route(job_no: Optional[int] = Query(None)):
    return await list_billings(job_no=job_no)


@billings_router.get('/{billing_id}', response_model=BillingSchema)
async def get_billing_route(billing_id: int):
    return await get_billing(billing_id)


@billings_router.post('', response_model=BillingSchema, status_code=201)
async def create_billing_route(
    job_no: int = Form(...),
    cancel_en_route: bool = Form(False),
    cancel_setup: bool = Form(False),
    billing_notes: Optional[str] = Form(None),
    videographer_hours_present: Optional[str] = Form(None),
    file_hours_length: Optional[str] = Form(None),
    files: List[UploadFile] = File(None),
):
    return await create_billing(
        job_no=job_no,
        cancel_en_route=cancel_en_route,
        cancel_setup=cancel_setup,
        billing_notes=billing_notes,
        videographer_hours_present=videographer_hours_present,
        file_hours_length=file_hours_length,
        files=files,
    )


@billings_router.post('/{billing_id}/upload', status_code=201)
async def upload_billing_files_route(
    billing_id: int,
    files: List[UploadFile] = File(...),
):
    return await upload_billing_files(billing_id, files)


@billings_router.put('/{billing_id}', response_model=BillingSchema)
async def update_billing_route(billing_id: int, billing_data: BillingUpdateSchema):
    return await update_billing(billing_id, billing_data)


@billings_router.delete('/{billing_id}', status_code=204)
async def delete_billing_route(billing_id: int):
    return await delete_billing(billing_id)
