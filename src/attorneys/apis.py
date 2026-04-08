from typing import List, Optional
from fastapi import Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from src.attorneys.models import Attorneys
from src.attorneys.utils import serialize_attorney, save_attorney_camera_upload, save_attorney_document_file
from src.core.file_utils import delete_stored_file_if_exists
from src.core.logger import logger
from fastapi import status
from sqlalchemy.orm import Session
from src.jobs.models import Jobs
from src.core.logger import logger
from src.jobs_tasks.models import JobsTasks
from src.core.context import get_context
from src.core.database import get_db
from src.core.timezone_utils import get_timezone_now

async def list_attorneys_by_job(job_no: int, db: Session) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')
        attorneys = (
            db.query(Attorneys)
            .join(Jobs, Attorneys.job_no == Jobs.job_no)
            .join(JobsTasks, JobsTasks.job_no == Jobs.job_no)
            .filter(
                Attorneys.job_no == job_no,
                Attorneys.is_archived == False,
                Jobs.is_archived == False,
                JobsTasks.rsrc_no == current_rsrc_no,
                JobsTasks.is_archived == False
            )
            .order_by(Attorneys.id.asc())
            .all()
        )

        attorneys_data = [serialize_attorney(attorney) for attorney in attorneys]

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
        current_rsrc_no = get_context('rsrc_no')
        now = get_timezone_now()

        # Validate job exists and resource has access
        job = (
            db.query(Jobs.job_no)
            .join(JobsTasks, JobsTasks.job_no == Jobs.job_no)
            .filter(
                Jobs.job_no == job_no,
                Jobs.is_archived == False,
                JobsTasks.rsrc_no == current_rsrc_no,
                JobsTasks.is_archived == False
            )
            .first()
        )

        if not job:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Job not found or access denied",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )

        attorney = Attorneys(
            job_no=job_no,
            attorney_name=attorney_name,
            firm_name=firm_name,
            notes=notes,
            order_details=order_details,
            entered_by=current_rsrc_no,
            last_modified_by=current_rsrc_no,
            entered_at=now,
            last_modified_at=now
        )
        db.add(attorney)
        db.flush()

        # Handle file uploads after flush so the storage key can include attorney id.
        if document and document.filename:
            await save_attorney_document_file(attorney, document, current_rsrc_no)

        if camera_captured_file and camera_captured_file.filename:
            await save_attorney_camera_upload(attorney, camera_captured_file, current_rsrc_no)

        db.commit()
        db.refresh(attorney)

        attorney_data = serialize_attorney(attorney)
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
                "result": {}
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
        current_rsrc_no = get_context('rsrc_no')
        now = get_timezone_now()

        attorney = (
            db.query(Attorneys)
            .join(Jobs, Attorneys.job_no == Jobs.job_no)
            .join(JobsTasks, JobsTasks.job_no == Jobs.job_no)
            .filter(
                Attorneys.id == attorney_id,
                Attorneys.is_archived == False,
                Jobs.is_archived == False,
                JobsTasks.rsrc_no == current_rsrc_no,
                JobsTasks.is_archived == False
            )
            .first()
        )

        if not attorney:
            logger.error(f"Attorney with ID {attorney_id} not found or access denied")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Attorney with ID {attorney_id} not found or access denied",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )

        form_data = await request.form()
        document_field_sent = 'document' in form_data
        camera_field_sent = 'camera_captured_file' in form_data
        fields_updated = []

        # Text fields — dynamic update via setattr
        text_fields = {
            "attorney_name": attorney_name,
            "firm_name": firm_name,
            "notes": notes,
            "order_details": order_details,
        }
        for field, value in text_fields.items():
            if value is not None:
                setattr(attorney, field, value.strip() if isinstance(value, str) else value)
                fields_updated.append(field)

        # Document file handling
        if document_field_sent:
            delete_stored_file_if_exists(attorney.file_name_path, "document")
            if document and document.filename:
                await save_attorney_document_file(attorney, document, current_rsrc_no)
            else:
                attorney.file_name = None
                attorney.file_name_path = None
            fields_updated.append("document")

        # Camera file handling
        if camera_field_sent:
            delete_stored_file_if_exists(attorney.camera_captured_file_path, "camera_captured_file")
            if camera_captured_file and camera_captured_file.filename:
                await save_attorney_camera_upload(attorney, camera_captured_file, current_rsrc_no)
            else:
                attorney.camera_captured_file_name = None
                attorney.camera_captured_file_path = None
            fields_updated.append("camera_captured_file")

        attorney.last_modified_at = now
        attorney.last_modified_by = current_rsrc_no
        db.add(attorney)
        db.commit()

        attorney_data = serialize_attorney(attorney)
        message = (
            f"Attorney updated successfully. Fields updated: {', '.join(fields_updated)}"
            if fields_updated
            else "No changes provided. Attorney data remains unchanged."
        )

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
        current_rsrc_no = get_context('rsrc_no')
        now = get_timezone_now()

        attorney = (
            db.query(Attorneys)
            .join(Jobs, Attorneys.job_no == Jobs.job_no)
            .join(JobsTasks, JobsTasks.job_no == Jobs.job_no)
            .filter(
                Attorneys.id == attorney_id,
                Attorneys.is_archived == False,
                Jobs.is_archived == False,
                JobsTasks.rsrc_no == current_rsrc_no,
                JobsTasks.is_archived == False
            )
            .first()
        )

        if not attorney:
            logger.error(f"Attorney with ID {attorney_id} not found or access denied")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Attorney with ID {attorney_id} not found or access denied",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )

        attorney.is_archived = True
        attorney.last_modified_at = now
        attorney.last_modified_by = current_rsrc_no

        delete_stored_file_if_exists(attorney.file_name_path, "document")
        delete_stored_file_if_exists(attorney.camera_captured_file_path, "camera_captured_file")

        attorney.file_name = None
        attorney.file_name_path = None
        attorney.camera_captured_file_name = None
        attorney.camera_captured_file_path = None
        
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
        db.rollback()
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
