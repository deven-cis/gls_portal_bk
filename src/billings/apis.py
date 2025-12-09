from typing import List, Optional
from fastapi import Depends, HTTPException, status, UploadFile, File, Form

from src.auth.utils import get_current_user
from src.billings.models import Billings
from src.billings.schema import BillingCreateSchema, BillingUpdateSchema
from src.jobs.models import Jobs
from src.additional_documents.models import AdditionalDocuments
from src.core.file_utils import save_multiple_files


async def list_billings(
    job_no: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
) -> List[Billings]:
    try:
        filters = {"is_archived": False}
        if job_no:
            filters["job_no"] = job_no
        return Billings.fetch_records(filters)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def get_billing(
    billing_id: int,
    current_user: dict = Depends(get_current_user),
) -> Billings:
    try:
        billing = Billings.get(billing_id)
        if not billing or billing.is_archived:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Billing with ID {billing_id} not found"
            )
        return billing
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def create_billing(
    job_no: int = Form(...),
    cancel_en_route: bool = Form(False),
    cancel_setup: bool = Form(False),
    billing_notes: Optional[str] = Form(None),
    videographer_hours_present: Optional[str] = Form(None),
    file_hours_length: Optional[str] = Form(None),
    files: List[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
) -> Billings:
    try:
        job = Jobs.get_queryset().filter(Jobs.job_no == job_no).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with job_no {job_no} not found"
            )
        
        billing = Billings(
            job_no=job_no,
            cancel_en_route=cancel_en_route,
            cancel_setup=cancel_setup,
            billing_notes=billing_notes,
            videographer_hours_present=videographer_hours_present,
            file_hours_length=file_hours_length,
        )
        billing = Billings.save(billing)
        
        if files:
            saved_files = await save_multiple_files(files, "billings")
            for file_name, file_path in saved_files:
                doc = AdditionalDocuments(
                    job_no=job_no,
                    billing_id=billing.id,
                    file_name=file_name,
                    file_path=file_path,
                )
                AdditionalDocuments.save(doc)
        
        return billing
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def update_billing(
    billing_id: int,
    billing_data: BillingUpdateSchema,
    current_user: dict = Depends(get_current_user),
) -> Billings:
    try:
        billing = Billings.get(billing_id)
        if not billing or billing.is_archived:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Billing with ID {billing_id} not found"
            )
        
        for field, value in billing_data.dict(exclude_unset=True).items():
            setattr(billing, field, value)
        
        return Billings.save(billing)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def upload_billing_files(
    billing_id: int,
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
) -> dict:
    try:
        billing = Billings.get(billing_id)
        if not billing or billing.is_archived:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Billing with ID {billing_id} not found"
            )
        
        saved_files = await save_multiple_files(files, "billings")
        for file_name, file_path in saved_files:
            doc = AdditionalDocuments(
                job_no=billing.job_no,
                billing_id=billing.id,
                file_name=file_name,
                file_path=file_path,
            )
            AdditionalDocuments.save(doc)
        
        return {"message": f"Successfully uploaded {len(saved_files)} file(s)"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def delete_billing(
    billing_id: int,
    current_user: dict = Depends(get_current_user),
) -> None:
    try:
        billing = Billings.get(billing_id)
        if not billing or billing.is_archived:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Billing with ID {billing_id} not found"
            )
        
        billing.is_archived = True
        Billings.save(billing)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
