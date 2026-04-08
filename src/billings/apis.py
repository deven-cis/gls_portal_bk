from typing import List, Optional
from fastapi import HTTPException, status, UploadFile, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from src.billings.models import Billings
from src.billings.utils import serialize_billing_with_documents
from src.additional_documents.models import AdditionalDocuments
from src.core.file_utils import delete_stored_file_if_exists, save_billing_camera_file, save_billing_documents
from src.core.logger import logger
from src.core.timezone_utils import get_timezone_now
from src.core.context import get_context
from src.jobs.models import Jobs
from src.jobs_tasks.models import JobsTasks
from src.jobs.models import Jobs

async def get_billing_by_job(job_no: int, db: Session) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')

        billing = (
            db.query(Billings)
            .join(Jobs, Billings.job_no == Jobs.job_no)
            .join(JobsTasks, JobsTasks.job_no == Jobs.job_no)
            .filter(
                Billings.job_no == job_no,
                Billings.is_archived == False,
                Jobs.is_archived == False,
                JobsTasks.rsrc_no == current_rsrc_no,
                JobsTasks.is_archived == False
            )
            .first()
        )

        if not billing:
            logger.info(f"Billing for job_no {job_no} not found")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": f"Billing for job_no {job_no} not found",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_200_OK
            )

        documents = (
            db.query(AdditionalDocuments)
            .filter(
                AdditionalDocuments.billing_id == billing.id,
                AdditionalDocuments.is_archived == False
            )
            .all()
        )

        billing_data = serialize_billing_with_documents(billing, documents)

        logger.info(
            f"Successfully retrieved billing for job {job_no} "
            f"(billing_id: {billing.id}) with {len(documents)} document(s)"
        )

        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": f"Billing for job {job_no} found with {len(documents)} document(s)",
                "success": True,
                "result": billing_data
            },
            status_code=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(f"Error getting billing for job {job_no}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to get billing: {str(e)}",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


async def create_billing(
    job_no: int,
    cancel_en_route: bool,
    cancel_setup: bool,
    billing_notes: Optional[str],
    videographer_hours_present: Optional[str],
    file_hours_length: Optional[str],
    files: Optional[List[UploadFile]],
    db: Session,
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
            logger.error(f"Job with job_no {job_no} not found")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Job with job_no {job_no} not found",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Create billing
        billing = Billings()
        billing_payload = {
            "job_no": job_no,
            "cancel_en_route": cancel_en_route,
            "cancel_setup": cancel_setup,
            "billing_notes": billing_notes,
            "videographer_hours_present": videographer_hours_present,
            "file_hours_length": file_hours_length,
            "entered_by": current_rsrc_no,
            "last_modified_by": current_rsrc_no,
            "entered_at": now,
            "last_modified_at": now
        }
        for key, value in billing_payload.items():
            if value is not None:
                setattr(billing, key, value)

        db.add(billing)
        db.flush()  # get billing.id before commit

        if camera_captured_file and camera_captured_file.filename:
            billing.camera_captured_file_name, billing.camera_captured_file_path = await save_billing_camera_file(
                camera_captured_file,
                rsrc_no=current_rsrc_no,
                job_no=job_no,
                billing_id=billing.id,
            )

        # Handle additional documents
        documents_created = 0
        if files:
            saved_files = await save_billing_documents(
                files,
                rsrc_no=current_rsrc_no,
                job_no=job_no,
                billing_id=billing.id,
            )
            for file_name, file_path in saved_files:
                doc = AdditionalDocuments()
                doc_payload = {
                    "job_no": job_no,
                    "billing_id": billing.id,
                    "file_name": file_name,
                    "file_path": file_path,
                    "entered_by": current_rsrc_no,
                    "last_modified_by": current_rsrc_no,
                    "entered_at": now,
                    "last_modified_at": now
                }
                for key, value in doc_payload.items():
                    setattr(doc, key, value)
                db.add(doc)
                documents_created += 1

        db.commit()
        db.refresh(billing)

        documents = (
            db.query(AdditionalDocuments)
            .filter(
                AdditionalDocuments.billing_id == billing.id,
                AdditionalDocuments.is_archived == False
            )
            .all()
        )
        billing_data = serialize_billing_with_documents(billing, documents)
        message = f"Billing created successfully with {documents_created} document(s)" if documents_created else "Billing created successfully"

        logger.info(f"Billing created successfully for job {job_no} with {documents_created} document(s)")
        return JSONResponse(
            content={
                "status_code": status.HTTP_201_CREATED,
                "message": message,
                "success": True,
                "result": billing_data
            },
            status_code=status.HTTP_201_CREATED
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating billing for job {job_no}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to create billing: {str(e)}",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


async def update_billing(
    billing_id: int,
    request: Request,
    job_no: Optional[int],
    cancel_en_route: Optional[str],
    cancel_setup: Optional[str],
    billing_notes: Optional[str],
    videographer_hours_present: Optional[str],
    file_hours_length: Optional[str],
    files: Optional[List[UploadFile]],
    db: Session,
    camera_captured_file: Optional[UploadFile] = None,
) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')
        now = get_timezone_now()

        billing = (
            db.query(Billings)
            .join(Jobs, Billings.job_no == Jobs.job_no)
            .join(JobsTasks, JobsTasks.job_no == Jobs.job_no)
            .filter(
                Billings.id == billing_id,
                Billings.is_archived == False,
                Jobs.is_archived == False,
                JobsTasks.rsrc_no == current_rsrc_no,
                JobsTasks.is_archived == False
            )
            .first()
        )

        if not billing:
            logger.error(f"Billing with ID {billing_id} not found or access denied")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Billing with ID {billing_id} not found or access denied",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )

        fields_updated = []
        form_data = await request.form()

        # Validate job_no if provided
        if job_no is not None:
            job_exists = (
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
            if not job_exists:
                logger.error(f"Job with job_no {job_no} not found or access denied")
                return JSONResponse(
                    content={
                        "status_code": status.HTTP_404_NOT_FOUND,
                        "message": f"Job with job_no {job_no} not found or access denied",
                        "success": False,
                        "result": {}
                    },
                    status_code=status.HTTP_404_NOT_FOUND
                )
            billing.job_no = job_no
            fields_updated.append("job_no")

        # Boolean fields
        bool_fields = {
            "cancel_en_route": cancel_en_route,
            "cancel_setup": cancel_setup
        }
        for field, value in bool_fields.items():
            if value is not None:
                setattr(billing, field, value.lower() in ['true', '1', 'yes'])
                fields_updated.append(field)

        # Text fields
        text_fields = {
            "billing_notes": billing_notes,
            "videographer_hours_present": videographer_hours_present,
            "file_hours_length": file_hours_length
        }
        for field, value in text_fields.items():
            if value is not None:
                setattr(billing, field, value.strip() if isinstance(value, str) else value)
                fields_updated.append(field)

        # Camera file handling
        if 'camera_captured_file' in form_data:
            delete_stored_file_if_exists(billing.camera_captured_file_path, "camera_captured_file")
            if camera_captured_file and camera_captured_file.filename:
                billing.camera_captured_file_name, billing.camera_captured_file_path = await save_billing_camera_file(
                    camera_captured_file,
                    rsrc_no=current_rsrc_no,
                    job_no=billing.job_no,
                    billing_id=billing.id,
                )
            else:
                billing.camera_captured_file_name = None
                billing.camera_captured_file_path = None
            fields_updated.append("camera_captured_file")

        # Remove documents
        documents_removed = 0
        remove_documents = form_data.getlist("remove_documents") if "remove_documents" in form_data else []
        for doc_id_str in remove_documents:
            try:
                doc = (
                    db.query(AdditionalDocuments)
                    .filter(
                        AdditionalDocuments.id == int(doc_id_str),
                        AdditionalDocuments.billing_id == billing_id,
                        AdditionalDocuments.is_archived == False
                    )
                    .first()
                )
                if doc:
                    delete_stored_file_if_exists(doc.file_path, "document")
                    doc.is_archived = True
                    doc.last_modified_at = now
                    doc.last_modified_by = current_rsrc_no
                    db.add(doc)
                    documents_removed += 1
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid document ID: {doc_id_str}, error: {str(e)}")
                continue

        if documents_removed > 0:
            fields_updated.append(f"documents (removed {documents_removed})")

        # Upload new documents
        documents_uploaded = 0
        if files:
            saved_files = await save_billing_documents(
                files,
                rsrc_no=current_rsrc_no,
                job_no=billing.job_no,
                billing_id=billing.id,
            )
            for file_name, file_path in saved_files:
                doc = AdditionalDocuments()
                doc_payload = {
                    "job_no": billing.job_no,
                    "billing_id": billing.id,
                    "file_name": file_name,
                    "file_path": file_path,
                    "entered_by": current_rsrc_no,
                    "last_modified_by": current_rsrc_no,
                    "entered_at": now,
                    "last_modified_at": now
                }
                for key, value in doc_payload.items():
                    setattr(doc, key, value)
                db.add(doc)
                documents_uploaded += 1

        if documents_uploaded > 0:
            fields_updated.append(f"documents (uploaded {documents_uploaded})")

        billing.last_modified_at = now
        billing.last_modified_by = current_rsrc_no
        db.add(billing)
        db.commit()
        db.refresh(billing)

        documents = (
            db.query(AdditionalDocuments)
            .filter(
                AdditionalDocuments.billing_id == billing.id,
                AdditionalDocuments.is_archived == False
            )
            .all()
        )
        billing_data = serialize_billing_with_documents(billing, documents)
        message = (
            f"Billing updated successfully. Fields updated: {', '.join(fields_updated)}"
            if fields_updated
            else "No changes provided. Billing data remains unchanged."
        )

        logger.info(f"Billing updated successfully for billing {billing_id}")
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": message,
                "success": True,
                "result": billing_data
            },
            status_code=status.HTTP_200_OK
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error updating billing {billing_id}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to update billing: {str(e)}",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


async def delete_billing(billing_id: int, db: Session) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')
        now = get_timezone_now()

        billing = (
            db.query(Billings)
            .join(Jobs, Billings.job_no == Jobs.job_no)
            .join(JobsTasks, JobsTasks.job_no == Jobs.job_no)
            .filter(
                Billings.id == billing_id,
                Billings.is_archived == False,
                Jobs.is_archived == False,
                JobsTasks.rsrc_no == current_rsrc_no,
                JobsTasks.is_archived == False
            )
            .first()
        )

        if not billing:
            logger.error(f"Billing with ID {billing_id} not found or access denied")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Billing with ID {billing_id} not found or access denied",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )

        delete_stored_file_if_exists(billing.camera_captured_file_path, "camera_captured_file")
        billing.camera_captured_file_name = None
        billing.camera_captured_file_path = None

        documents = (
            db.query(AdditionalDocuments)
            .filter(
                AdditionalDocuments.billing_id == billing_id,
                AdditionalDocuments.is_archived == False
            )
            .all()
        )
        for doc in documents:
            delete_stored_file_if_exists(doc.file_path, "document")
            doc.is_archived = True
            doc.last_modified_at = now
            doc.last_modified_by = current_rsrc_no
            db.add(doc)

        billing.is_archived = True
        billing.last_modified_at = now
        billing.last_modified_by = current_rsrc_no
        db.add(billing)
        db.commit()

        logger.info(f"Billing {billing_id} and associated documents deleted successfully")
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": f"Billing with ID {billing_id} deleted successfully",
                "success": True,
                "result": {}
            },
            status_code=status.HTTP_200_OK
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting billing {billing_id}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to delete billing: {str(e)}",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )