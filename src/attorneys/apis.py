from typing import List, Optional
from fastapi import Request, UploadFile
from fastapi.responses import JSONResponse
from pathlib import Path
from sqlalchemy.orm import Session
from src.attorneys.models import Attorneys
from src.core.file_utils import save_file, save_image_file
from src.attorneys.schema import AttorneySchema
from src.core.logger import logger
from fastapi import status
from sqlalchemy.orm import Session
from src.jobs.models import Jobs
from src.core.context import get_context
from src.core.database import get_db
from src.core.timezone_utils import get_timezone_now

async def list_attorneys_by_job(job_no: int, db: Session) -> JSONResponse:
    try:
        user_entered_by = get_context('entered_by')
        attorneys = db.query(Attorneys).filter(
            Attorneys.job_no == job_no,
            Attorneys.is_archived == False
        ).order_by(Attorneys.id.asc()).all()
        
        attorneys_data = [AttorneySchema.model_validate(attorney).model_dump(mode='json') for attorney in attorneys]
        
        logger.info(f"Successfully got {len(attorneys_data)} attorneys for job {job_no}")
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
    db: Session,
    document: Optional[UploadFile] = None,
    camera_captured_file: Optional[UploadFile] = None,
) -> JSONResponse:
    try:
        user_entered_by = get_context('entered_by')
        now = get_timezone_now()
        job = db.query(Jobs).filter(Jobs.job_no == job_no).first()
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
        camera_captured_file_name = None
        camera_captured_file_path = None
        
        if document and document.filename:
            file_name, file_name_path = await save_file(document, "attorneys")
        
        if camera_captured_file and camera_captured_file.filename:
            camera_captured_file_name, camera_captured_file_path = await save_image_file(camera_captured_file, "attorneys")
        
        attorney = Attorneys(
            job_no=job_no,
            attorney_name=attorney_name,
            firm_name=firm_name,
            notes=notes,
            order_details=order_details,
            file_name=file_name,
            file_name_path=file_name_path,
            camera_captured_file_name=camera_captured_file_name,
            camera_captured_file_path=camera_captured_file_path,
            entered_by=user_entered_by,
            last_modified_by=user_entered_by,
            entered_at=now,
            last_modified_at=now
        )
        db.add(attorney)
        db.commit()
        db.refresh(attorney)
        
        attorney_data = AttorneySchema.model_validate(attorney).model_dump(mode='json')
        logger.info(f"Successfully created attorney {attorney_name} for job {job_no}")
        return JSONResponse(
            content={
                "status_code": status.HTTP_201_CREATED,
                "message": "Attorney created successfully",
                "success": True,
                "result": attorney_data
            },
            status_code=status.HTTP_201_CREATED
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating attorney {attorney_name} for job {job_no}: {str(e)}", exc_info=True)
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
    db: Session,
    attorney_name: Optional[str] = None,
    firm_name: Optional[str] = None,
    notes: Optional[str] = None,
    order_details: Optional[str] = None,
    document: Optional[UploadFile] = None,
    camera_captured_file: Optional[UploadFile] = None,
) -> JSONResponse:
    try:
        user_entered_by = get_context('entered_by')
        now = get_timezone_now()
        attorney = db.query(Attorneys).filter(
            Attorneys.id == attorney_id,
            Attorneys.is_archived == False
        ).first()
        
        if not attorney:
            logger.error(f"Attorney with ID {attorney_id} not found")
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
        camera_field_sent = 'camera_captured_file' in form_data
        
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
        
        if camera_field_sent:
            if camera_captured_file and camera_captured_file.filename:
                # Delete old camera file if exists
                if attorney.camera_captured_file_path:
                    try:
                        old_camera_file_path = Path(attorney.camera_captured_file_path)
                        if old_camera_file_path.exists():
                            old_camera_file_path.unlink()
                            logger.info(f"Deleted old camera file: {attorney.camera_captured_file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to delete old camera file {attorney.camera_captured_file_path}: {str(e)}")
                
                camera_captured_file_name, camera_captured_file_path = await save_image_file(camera_captured_file, "attorneys")
                attorney.camera_captured_file_name = camera_captured_file_name
                attorney.camera_captured_file_path = camera_captured_file_path
                fields_updated.append("camera_captured_file")
            else:
                # Remove camera file if field sent but empty
                if attorney.camera_captured_file_path:
                    try:
                        camera_file_path = Path(attorney.camera_captured_file_path)
                        if camera_file_path.exists():
                            camera_file_path.unlink()
                            logger.info(f"Deleted camera file: {attorney.camera_captured_file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to delete camera file {attorney.camera_captured_file_path}: {str(e)}")
                
                attorney.camera_captured_file_name = None
                attorney.camera_captured_file_path = None
                fields_updated.append("camera_captured_file")
        
        attorney.last_modified_at = now
        attorney.last_modified_by = user_entered_by
        db.add(attorney)
        db.commit()
        
        attorney_data = AttorneySchema.model_validate(attorney).model_dump(mode='json')
        
        if fields_updated:
            message = f"Attorney updated successfully. Fields updated: {', '.join(fields_updated)}"
        else:
            message = "No changes provided. Attorney data remains unchanged."
        logger.info(f"Successfully updated attorney {attorney_id}")
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": message,
                "success": True,
                "result": attorney_data
            },
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating attorney {attorney_id}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to update attorney: {str(e)}",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


async def delete_attorney(attorney_id: int, db: Session) -> JSONResponse:
    try:
        user_entered_by = get_context('entered_by')
        now = get_timezone_now()
        attorney = db.query(Attorneys).filter(
            Attorneys.id == attorney_id,
            Attorneys.is_archived == False
        ).first()
        if not attorney:
            logger.error(f"Attorney with ID {attorney_id} not found")
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
        attorney.last_modified_at = now
        attorney.last_modified_by = user_entered_by
        db.add(attorney)
        db.commit()

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
