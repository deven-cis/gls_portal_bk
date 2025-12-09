from typing import List, Optional
from fastapi import Depends, HTTPException, status, UploadFile, File, Form
from decimal import Decimal

from src.auth.utils import get_current_user
from src.equipment_time.models import EquipmentTime
from src.equipment_time.schema import EquipmentTimeCreateSchema, EquipmentTimeUpdateSchema
from src.jobs.models import Jobs
from src.additional_documents.models import AdditionalDocuments
from src.core.file_utils import save_multiple_files


async def list_equipment_times(
    job_no: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
) -> List[EquipmentTime]:
    try:
        filters = {"is_archived": False}
        if job_no:
            filters["job_no"] = job_no
        return EquipmentTime.fetch_records(filters)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def get_equipment_time(
    equipment_time_id: int,
    current_user: dict = Depends(get_current_user),
) -> EquipmentTime:
    try:
        equipment_time = EquipmentTime.get(equipment_time_id)
        if not equipment_time or equipment_time.is_archived:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"EquipmentTime with ID {equipment_time_id} not found"
            )
        return equipment_time
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def create_equipment_time(
    job_no: int = Form(...),
    laptop_used: bool = Form(False),
    pip_used: bool = Form(False),
    exhibit_tech: bool = Form(False),
    parking_cost: Optional[str] = Form(None),
    time_after: Optional[str] = Form(None),
    files: List[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
) -> EquipmentTime:
    try:
        job = Jobs.get_queryset().filter(Jobs.job_no == job_no).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with job_no {job_no} not found"
            )
        
        parking_cost_decimal = Decimal(parking_cost) if parking_cost else Decimal('0.00')
        
        equipment_time = EquipmentTime(
            job_no=job_no,
            laptop_used=laptop_used,
            pip_used=pip_used,
            exhibit_tech=exhibit_tech,
            parking_cost=parking_cost_decimal,
            time_after=time_after,
        )
        equipment_time = EquipmentTime.save(equipment_time)
        
        if files:
            saved_files = await save_multiple_files(files, "equipment_time")
            for file_name, file_path in saved_files:
                doc = AdditionalDocuments(
                    job_no=job_no,
                    equipment_time_id=equipment_time.id,
                    file_name=file_name,
                    file_path=file_path,
                )
                AdditionalDocuments.save(doc)
        
        return equipment_time
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def update_equipment_time(
    equipment_time_id: int,
    equipment_time_data: EquipmentTimeUpdateSchema,
    current_user: dict = Depends(get_current_user),
) -> EquipmentTime:
    try:
        equipment_time = EquipmentTime.get(equipment_time_id)
        if not equipment_time or equipment_time.is_archived:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"EquipmentTime with ID {equipment_time_id} not found"
            )
        
        for field, value in equipment_time_data.dict(exclude_unset=True).items():
            setattr(equipment_time, field, value)
        
        return EquipmentTime.save(equipment_time)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def upload_equipment_time_files(
    equipment_time_id: int,
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
) -> dict:
    try:
        equipment_time = EquipmentTime.get(equipment_time_id)
        if not equipment_time or equipment_time.is_archived:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"EquipmentTime with ID {equipment_time_id} not found"
            )
        
        saved_files = await save_multiple_files(files, "equipment_time")
        for file_name, file_path in saved_files:
            doc = AdditionalDocuments(
                job_no=equipment_time.job_no,
                equipment_time_id=equipment_time.id,
                file_name=file_name,
                file_path=file_path,
            )
            AdditionalDocuments.save(doc)
        
        return {"message": f"Successfully uploaded {len(saved_files)} file(s)"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def delete_equipment_time(
    equipment_time_id: int,
    current_user: dict = Depends(get_current_user),
) -> None:
    try:
        equipment_time = EquipmentTime.get(equipment_time_id)
        if not equipment_time or equipment_time.is_archived:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"EquipmentTime with ID {equipment_time_id} not found"
            )
        
        equipment_time.is_archived = True
        EquipmentTime.save(equipment_time)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
