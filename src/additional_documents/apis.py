from typing import List, Optional
from fastapi import Depends, HTTPException, status

from src.auth.utils import get_current_user
from src.additional_documents.models import AdditionalDocuments


async def list_additional_documents(
    job_no: Optional[int] = None,
    billing_id: Optional[int] = None,
    equipment_time_id: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
) -> List[AdditionalDocuments]:
    try:
        filters = {"is_archived": False}
        if job_no:
            filters["job_no"] = job_no
        if billing_id:
            filters["billing_id"] = billing_id
        if equipment_time_id:
            filters["equipment_time_id"] = equipment_time_id
        return AdditionalDocuments.fetch_records(filters)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def get_additional_document(
    document_id: int,
    current_user: dict = Depends(get_current_user),
) -> AdditionalDocuments:
    try:
        document = AdditionalDocuments.get(document_id)
        if not document or document.is_archived:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"AdditionalDocument with ID {document_id} not found"
            )
        return document
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def delete_additional_document(
    document_id: int,
    current_user: dict = Depends(get_current_user),
) -> None:
    try:
        document = AdditionalDocuments.get(document_id)
        if not document or document.is_archived:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"AdditionalDocument with ID {document_id} not found"
            )
        
        document.is_archived = True
        AdditionalDocuments.save(document)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
