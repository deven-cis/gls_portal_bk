from typing import List, Optional
from fastapi import Query, Form, File, UploadFile

from src.attorneys.apis import (
    attorneys_router,  # Import router from apis.py where create_attorney route is defined
    list_attorneys_by_job,
    delete_attorney,
    upload_attorney_file,
)
from src.attorneys.schema import AttorneySchema



@attorneys_router.post('/{attorney_id}/upload', response_model=AttorneySchema)
async def upload_attorney_file_route(
    attorney_id: int,
    file: UploadFile = File(...),
):
    return await upload_attorney_file(attorney_id, file)



@attorneys_router.delete('/{attorney_id}', status_code=204)
async def delete_attorney_route(attorney_id: int):
    return await delete_attorney(attorney_id)
