from typing import List, Optional
from fastapi import Depends, HTTPException, status, UploadFile, File, Form

from src.auth.utils import get_current_user
from src.attorneys.models import Attorneys
from src.jobs.models import Jobs
from src.core.file_utils import save_file


async def list_attorneys(
    job_no: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
) -> List[Attorneys]:
    try:
        filters = {"is_archived": False}
        if job_no:
            filters["job_no"] = job_no
        return Attorneys.fetch_records(filters)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def get_attorney(
    attorney_id: int,
    current_user: dict = Depends(get_current_user),
) -> Attorneys:
    try:
        attorney = Attorneys.get(attorney_id)
        if not attorney or attorney.is_archived:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Attorney with ID {attorney_id} not found"
            )
        return attorney
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def create_attorney(
    job_no: int = Form(...),
    attorney_name: str = Form(...),
    firm_name: str = Form(...),
    notes: str = Form(...),
    order_details: str = Form(...),
    file: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
) -> Attorneys:
    try:
        job = Jobs.get_queryset().filter(Jobs.job_no == job_no).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with job_no {job_no} not found"
            )
        
        file_name = None
        file_name_path = None
        
        if file:
            file_name, file_name_path = await save_file(file, "attorneys")
        
        attorney = Attorneys(
            job_no=job_no,
            attorney_name=attorney_name,
            firm_name=firm_name,
            notes=notes,
            order_details=order_details,
            file_name=file_name,
            file_name_path=file_name_path,
        )
        return Attorneys.save(attorney)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def update_attorney(
    attorney_id: int,
    attorney_name: Optional[str] = Form(None),
    firm_name: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    order_details: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
) -> Attorneys:
    try:
        db = Attorneys.get_session()
        attorney = db.query(Attorneys).filter(Attorneys.id == attorney_id).first()
        
        if not attorney or attorney.is_archived:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Attorney with ID {attorney_id} not found"
            )
        
        if attorney_name is not None:
            attorney.attorney_name = attorney_name
        if firm_name is not None:
            attorney.firm_name = firm_name
        if notes is not None:
            attorney.notes = notes
        if order_details is not None:
            attorney.order_details = order_details
        
        if file:
            file_name, file_name_path = await save_file(file, "attorneys")
            attorney.file_name = file_name
            attorney.file_name_path = file_name_path
        
        from src.core.context import get_context
        from datetime import datetime
        entered_by = get_context('entered_by') or 0
        attorney.last_modified_at = datetime.now()
        attorney.last_modified_by = entered_by
        
        db.commit()
        db.refresh(attorney)
        return attorney
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def upload_attorney_file(
    attorney_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
) -> Attorneys:
    try:
        db = Attorneys.get_session()
        attorney = db.query(Attorneys).filter(Attorneys.id == attorney_id).first()
        
        if not attorney or attorney.is_archived:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Attorney with ID {attorney_id} not found"
            )
        
        file_name, file_name_path = await save_file(file, "attorneys")
        attorney.file_name = file_name
        attorney.file_name_path = file_name_path
        
        db.commit()
        db.refresh(attorney)
        return attorney
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def delete_attorney(
    attorney_id: int,
    current_user: dict = Depends(get_current_user),
) -> None:
    try:
        attorney = Attorneys.get(attorney_id)
        if not attorney or attorney.is_archived:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Attorney with ID {attorney_id} not found"
            )
        
        attorney.is_archived = True
        Attorneys.save(attorney)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
