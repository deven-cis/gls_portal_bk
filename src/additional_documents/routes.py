from typing import List, Optional
from fastapi import APIRouter, Query

from src.additional_documents.apis import (
    list_additional_documents, get_additional_document, delete_additional_document
)
from src.additional_documents.schema import AdditionalDocumentSchema


additional_documents_router = APIRouter(prefix='/additional-documents', tags=['additional-documents'])


@additional_documents_router.get('', response_model=List[AdditionalDocumentSchema])
async def list_additional_documents_route(
    job_no: Optional[int] = Query(None),
    billing_id: Optional[int] = Query(None),
    equipment_time_id: Optional[int] = Query(None),
):
    return await list_additional_documents(
        job_no=job_no,
        billing_id=billing_id,
        equipment_time_id=equipment_time_id
    )


@additional_documents_router.get('/{document_id}', response_model=AdditionalDocumentSchema)
async def get_additional_document_route(document_id: int):
    return await get_additional_document(document_id)


@additional_documents_router.delete('/{document_id}', status_code=204)
async def delete_additional_document_route(document_id: int):
    return await delete_additional_document(document_id)
