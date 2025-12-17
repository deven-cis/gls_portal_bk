from typing import List, Optional
from fastapi import Depends, HTTPException, status, UploadFile, File, Form, APIRouter, Request
from fastapi.responses import JSONResponse
from pathlib import Path
from src.auth.utils import get_current_user
from src.attorneys.models import Attorneys
from src.jobs.models import Jobs
from src.core.file_utils import save_file
from src.attorneys.schema import AttorneySchema
from src.core.logger import logger

attorneys_router = APIRouter(prefix='/attorneys', tags=['attorneys'])


@attorneys_router.get('/list/{job_no}', status_code=200)
async def list_attorneys_by_job(
    job_no: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
   
    try:
        attorneys = Attorneys.get_queryset().filter(
            Attorneys.job_no == job_no,
            Attorneys.is_archived == False
        ).all()
        
        # Serialize all attorneys to Pydantic schemas
        attorneys_data = [AttorneySchema.model_validate(attorney).model_dump() for attorney in attorneys]
        
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": f"Found {len(attorneys_data)} attorney(s)",
                "success": True,
                "result": attorneys_data
            },
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to get attorneys: {str(e)}",
                "success": False,
                "result": []
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@attorneys_router.post('/create', status_code=201)
async def create_attorney(
    job_no: int = Form(...),
    attorney_name: str = Form(...),
    firm_name: str = Form(...),
    notes: str = Form(...),
    order_details: str = Form(...),
    document: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
):
    try:
        job = Jobs.get_queryset().filter(Jobs.job_no == job_no).first()
        if not job:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Job not found",
                    "result": []
                }
            )
        
        file_name = None
        file_name_path = None
        
        # Handle single document upload
        if document and document.filename:
            file_name, file_name_path = await save_file(document, "attorneys")
        
        attorney = Attorneys(
            job_no=job_no,
            attorney_name=attorney_name,
            firm_name=firm_name,
            notes=notes,
            order_details=order_details,
            file_name=file_name,
            file_name_path=file_name_path,
        )
        saved_attorney = Attorneys.save(attorney)
        
        # Serialize SQLAlchemy model to Pydantic schema
        attorney_data = AttorneySchema.model_validate(saved_attorney)
        
        return JSONResponse(
            content={
                "status_code": status.HTTP_201_CREATED,
                "message": "Attorney created successfully",
                "success": True,
                "result": attorney_data.model_dump()
            },
            status_code=status.HTTP_201_CREATED
        )
    except Exception as e:
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to create attorney: {str(e)}",
                "success": False,
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )   


@attorneys_router.put('/update/{attorney_id}', status_code=200)
async def update_attorney(
    attorney_id: int,
    request: Request,
    attorney_name: Optional[str] = Form(None),
    firm_name: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    order_details: Optional[str] = Form(None),
    document: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Update attorney. Only provided fields will be updated, others remain unchanged.
    Frontend sends: attorney_name, firm_name, notes, order_details, document (optional)
    
    Document handling:
    - If document file is sent with filename → upload/replace document
    - If document field is sent but empty (no file) → remove existing document
    - If document field is not sent at all → keep existing document unchanged
    """
    try:
        db = Attorneys.get_session()
        attorney = db.query(Attorneys).filter(
            Attorneys.id == attorney_id,
            Attorneys.is_archived == False
        ).first()
        
        if not attorney:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Attorney with ID {attorney_id} not found",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Read form data to check if document field was explicitly sent
        form_data = await request.form()
        document_field_sent = 'document' in form_data
        
        # Track which fields were updated
        fields_updated = []
        
        # Update only fields that are provided (not None)
        if attorney_name is not None:
            # Handle empty strings - allow clearing the field
            if isinstance(attorney_name, str):
                attorney.attorney_name = attorney_name.strip() if attorney_name.strip() else attorney_name
            else:
                attorney.attorney_name = attorney_name
            fields_updated.append("attorney_name")
        
        if firm_name is not None:
            if isinstance(firm_name, str):
                attorney.firm_name = firm_name.strip() if firm_name.strip() else firm_name
            else:
                attorney.firm_name = firm_name
            fields_updated.append("firm_name")
        
        if notes is not None:
            if isinstance(notes, str):
                attorney.notes = notes.strip() if notes.strip() else notes
            else:
                attorney.notes = notes
            fields_updated.append("notes")
        
        if order_details is not None:
            if isinstance(order_details, str):
                attorney.order_details = order_details.strip() if order_details.strip() else order_details
            else:
                attorney.order_details = order_details
            fields_updated.append("order_details")
        
        # Handle document: upload, remove, or keep unchanged
        if document_field_sent:
            # Document field was explicitly sent in form
            if document and document.filename:
                # New file uploaded - replace existing document
                # Delete old file if exists
                if attorney.file_name_path:
                    try:
                        old_file_path = Path(attorney.file_name_path)
                        if old_file_path.exists():
                            old_file_path.unlink()
                            logger.info(f"Deleted old file: {attorney.file_name_path}")
                    except Exception as e:
                        logger.warning(f"Failed to delete old file {attorney.file_name_path}: {str(e)}")
                
                # Save new file
                file_name, file_name_path = await save_file(document, "attorneys")
                attorney.file_name = file_name
                attorney.file_name_path = file_name_path
                fields_updated.append("document")
            else:
                # Document field sent but no file (empty) - remove existing document
                if attorney.file_name_path:
                    try:
                        file_path = Path(attorney.file_name_path)
                        if file_path.exists():
                            file_path.unlink()
                            logger.info(f"Deleted file: {attorney.file_name_path}")
                    except Exception as e:
                        logger.warning(f"Failed to delete file {attorney.file_name_path}: {str(e)}")
                
                attorney.file_name = None
                attorney.file_name_path = None
                fields_updated.append("document")
        # If document_field_sent is False, document field was not sent - keep existing document unchanged
        
        attorney.save()
        
        # Serialize SQLAlchemy model to Pydantic schema
        attorney_data = AttorneySchema.model_validate(attorney)
        
        # Prepare response message
        if fields_updated:
            message = f"Attorney updated successfully. Fields updated: {', '.join(fields_updated)}"
        else:
            message = "No changes provided. Attorney data remains unchanged."
        
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": message,
                "success": True,
                "result": attorney_data.model_dump()
            },
            status_code=status.HTTP_200_OK
        )
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to update attorney: {str(e)}",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


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
