from typing import List, Optional
from fastapi import Request, UploadFile
from fastapi.responses import JSONResponse
from pathlib import Path
from sqlalchemy.orm import Session
from src.attorneys.models import Attorneys
from src.core.file_utils import save_file
from src.attorneys.schema import AttorneySchema
from src.core.logger import logger
from fastapi import status


async def list_attorneys_by_job(job_no: int, db: Session) -> JSONResponse:
    try:
        attorneys = db.query(Attorneys).filter(
            Attorneys.job_no == job_no,
            Attorneys.is_archived == False
        ).all()
        
        attorneys_data = [AttorneySchema.model_validate(attorney).model_dump(mode='json') for attorney in attorneys]
        
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
        logger.error(f"Error getting attorneys for job {job_no}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to get attorneys: {str(e)}",
                "success": False,
                "result": []
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


async def create_attorney(
    job_no: int,
    attorney_name: str,
    firm_name: str,
    notes: str,
    order_details: str,
    document: Optional[UploadFile] = None,
) -> JSONResponse:
    try:
        from src.jobs.models import Jobs
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
        
        attorney_data = AttorneySchema.model_validate(saved_attorney)
        
        return JSONResponse(
            content={
                "status_code": status.HTTP_201_CREATED,
                "message": "Attorney created successfully",
                "success": True,
                "result": attorney_data.model_dump(mode='json')
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


async def update_attorney(
    attorney_id: int,
    request: Request,
    attorney_name: Optional[str] = None,
    firm_name: Optional[str] = None,
    notes: Optional[str] = None,
    order_details: Optional[str] = None,
    document: Optional[UploadFile] = None,
) -> JSONResponse:
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
        
        form_data = await request.form()
        document_field_sent = 'document' in form_data
        
        fields_updated = []
        
        if attorney_name is not None:
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
        
        if document_field_sent:
            if document and document.filename:
                if attorney.file_name_path:
                    try:
                        old_file_path = Path(attorney.file_name_path)
                        if old_file_path.exists():
                            old_file_path.unlink()
                            logger.info(f"Deleted old file: {attorney.file_name_path}")
                    except Exception as e:
                        logger.warning(f"Failed to delete old file {attorney.file_name_path}: {str(e)}")
                
                file_name, file_name_path = await save_file(document, "attorneys")
                attorney.file_name = file_name
                attorney.file_name_path = file_name_path
                fields_updated.append("document")
            else:
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
        
        attorney.save()
        
        attorney_data = AttorneySchema.model_validate(attorney)
        
        if fields_updated:
            message = f"Attorney updated successfully. Fields updated: {', '.join(fields_updated)}"
        else:
            message = "No changes provided. Attorney data remains unchanged."
        
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": message,
                "success": True,
                "result": attorney_data.model_dump(mode='json')
            },
            status_code=status.HTTP_200_OK
        )
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


async def delete_attorney(attorney_id: int) -> JSONResponse:
    try:
        attorney = Attorneys.get_queryset().filter(Attorneys.id == attorney_id, Attorneys.is_archived == False).first()
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
        
        attorney.is_archived = True
        attorney.save()   
        logger.info(f"Successfully deleted attorney {attorney_id}")
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": f"Attorney with ID {attorney_id} deleted successfully",
                "success": True,
                "result": {}
            },
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        logger.error(f"Error deleting attorney {attorney_id}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to delete attorney: {str(e)}",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
