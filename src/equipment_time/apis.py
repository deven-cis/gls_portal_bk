from typing import List, Optional
from decimal import Decimal
from datetime import datetime
from fastapi import HTTPException, status, UploadFile, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from src.equipment_time.models import EquipmentTime
from src.equipment_time.utils import serialize_equipment_time_with_documents
from src.additional_documents.models import AdditionalDocuments
from src.core.file_utils import delete_stored_file_if_exists, save_equipment_time_camera_file, save_equipment_time_documents
from src.core.logger import logger
from src.core.context import get_context
from src.core.timezone_utils import get_timezone_now
from src.jobs_tasks.models import JobsTasks
from src.jobs.models import Jobs

async def get_equipment_time_by_job(job_no: int, db: Session) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')

        equipment_time = (
            db.query(EquipmentTime)
            .join(Jobs, EquipmentTime.job_no == Jobs.job_no)
            .join(JobsTasks, JobsTasks.job_no == Jobs.job_no)
            .filter(
                EquipmentTime.job_no == job_no,
                EquipmentTime.is_archived == False,
                Jobs.is_archived == False,
                JobsTasks.rsrc_no == current_rsrc_no,
                JobsTasks.is_archived == False
            )
            .first()
        )

        if not equipment_time:
            logger.warning(f"Equipment time for job_no {job_no} not found or access denied")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Equipment time for job_no {job_no} not found or access denied",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )

        documents = (
            db.query(AdditionalDocuments)
            .filter(
                AdditionalDocuments.equipment_time_id == equipment_time.id,
                AdditionalDocuments.is_archived == False
            )
            .all()
        )

        equipment_time_with_docs = serialize_equipment_time_with_documents(equipment_time, documents)

        logger.info(
            f"Successfully retrieved equipment_time for job {job_no} "
            f"(equipment_time_id: {equipment_time.id}) with {len(documents)} document(s)"
        )

        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": f"Equipment time for job {job_no} found with {len(documents)} document(s)",
                "success": True,
                "result": equipment_time_with_docs
            },
            status_code=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(f"Error getting equipment_time for job {job_no}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to get equipment_time: {str(e)}",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


async def create_equipment_time(
    job_no: int,
    laptop_used: bool,
    pip_used: bool,
    exhibit_tech: bool,
    parking_cost: Optional[str],
    time_after: Optional[str],
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

        # Create equipment time via setattr
        equipment_time = EquipmentTime()
        equipment_payload = {
            "job_no": job_no,
            "laptop_used": laptop_used,
            "pip_used": pip_used,
            "exhibit_tech": exhibit_tech,
            "parking_cost": Decimal(parking_cost) if parking_cost else Decimal('0.00'),
            "time_after": time_after,
            "entered_by": current_rsrc_no,
            "entered_at": now,
            "last_modified_by": current_rsrc_no,
            "last_modified_at": now
        }
        for key, value in equipment_payload.items():
            setattr(equipment_time, key, value)

        db.add(equipment_time)
        db.flush()  # get equipment_time.id before commit

        if camera_captured_file and camera_captured_file.filename:
            equipment_time.camera_captured_file_name, equipment_time.camera_captured_file_path = (
                await save_equipment_time_camera_file(
                    camera_captured_file,
                    rsrc_no=current_rsrc_no,
                    job_no=job_no,
                    equipment_time_id=equipment_time.id,
                )
            )

        # Handle additional documents
        documents_created = 0
        valid_files = [f for f in files if f and f.filename] if files else []
        if valid_files:
            saved_files = await save_equipment_time_documents(
                valid_files,
                rsrc_no=current_rsrc_no,
                job_no=job_no,
                equipment_time_id=equipment_time.id,
            )
            for file_name, file_path in saved_files:
                doc = AdditionalDocuments()
                doc_payload = {
                    "job_no": job_no,
                    "equipment_time_id": equipment_time.id,
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
        db.refresh(equipment_time)

        # Fetch saved documents
        documents = (
            db.query(AdditionalDocuments)
            .filter(
                AdditionalDocuments.equipment_time_id == equipment_time.id,
                AdditionalDocuments.is_archived == False
            )
            .all()
        )
        equipment_time_with_docs = serialize_equipment_time_with_documents(equipment_time, documents)

        message = f"Equipment time created successfully with {documents_created} document(s)" if documents_created else "Equipment time created successfully"
        logger.info(f"Equipment time created for job {job_no} with {documents_created} document(s)")

        return JSONResponse(
            content={
                "status_code": status.HTTP_201_CREATED,
                "message": message,
                "success": True,
                "result": equipment_time_with_docs
            },
            status_code=status.HTTP_201_CREATED
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating equipment_time for job {job_no}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to create equipment_time: {str(e)}",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


async def update_equipment_time(
    equipment_time_id: int,
    request: Request,
    laptop_used: Optional[str],
    pip_used: Optional[str],
    exhibit_tech: Optional[str],
    parking_cost: Optional[str],
    time_after: Optional[str],
    files: Optional[List[UploadFile]],
    db: Session,
    camera_captured_file: Optional[UploadFile] = None,
) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')
        now = get_timezone_now()

        equipment_time = (
            db.query(EquipmentTime)
            .join(Jobs, EquipmentTime.job_no == Jobs.job_no)
            .join(JobsTasks, JobsTasks.job_no == Jobs.job_no)
            .filter(
                EquipmentTime.id == equipment_time_id,
                EquipmentTime.is_archived == False,
                Jobs.is_archived == False,
                JobsTasks.rsrc_no == current_rsrc_no,
                JobsTasks.is_archived == False
            )
            .first()
        )

        if not equipment_time:
            logger.error(f"Equipment time with ID {equipment_time_id} not found or access denied")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Equipment time with ID {equipment_time_id} not found or access denied",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )

        fields_updated = []
        form_data = await request.form()

        # Boolean fields
        bool_fields = {
            "laptop_used": laptop_used,
            "pip_used": pip_used,
            "exhibit_tech": exhibit_tech
        }
        for field, value in bool_fields.items():
            if value is not None:
                setattr(equipment_time, field, value.lower() in ['true', '1', 'yes'])
                fields_updated.append(field)

        # Parking cost
        if parking_cost is not None:
            try:
                equipment_time.parking_cost = Decimal(parking_cost) if parking_cost else Decimal('0.00')
                fields_updated.append("parking_cost")
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid parking_cost value: {parking_cost}, error: {str(e)}")

        # Time after
        if time_after is not None:
            equipment_time.time_after = time_after.strip() if isinstance(time_after, str) else time_after
            fields_updated.append("time_after")

        # Remove documents
        documents_removed = 0
        for doc_id_str in form_data.getlist("remove_documents"):
            try:
                doc = (
                    db.query(AdditionalDocuments)
                    .filter(
                        AdditionalDocuments.id == int(doc_id_str),
                        AdditionalDocuments.equipment_time_id == equipment_time_id,
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
        valid_files = [f for f in files if f and f.filename] if files else []
        if valid_files:
            saved_files = await save_equipment_time_documents(
                valid_files,
                rsrc_no=current_rsrc_no,
                job_no=equipment_time.job_no,
                equipment_time_id=equipment_time.id,
            )
            for file_name, file_path in saved_files:
                doc = AdditionalDocuments()
                for key, value in {
                    "job_no": equipment_time.job_no,
                    "equipment_time_id": equipment_time.id,
                    "file_name": file_name,
                    "file_path": file_path,
                    "entered_by": current_rsrc_no,
                    "last_modified_by": current_rsrc_no,
                    "entered_at": now,
                    "last_modified_at": now
                }.items():
                    setattr(doc, key, value)
                db.add(doc)
                documents_uploaded += 1

        if documents_uploaded > 0:
            fields_updated.append(f"documents (uploaded {documents_uploaded})")

        # Camera file handling
        if 'camera_captured_file' in form_data:
            delete_stored_file_if_exists(equipment_time.camera_captured_file_path, "camera_captured_file")
            if camera_captured_file and camera_captured_file.filename:
                equipment_time.camera_captured_file_name, equipment_time.camera_captured_file_path = (
                    await save_equipment_time_camera_file(
                        camera_captured_file,
                        rsrc_no=current_rsrc_no,
                        job_no=equipment_time.job_no,
                        equipment_time_id=equipment_time.id,
                    )
                )
            else:
                equipment_time.camera_captured_file_name = None
                equipment_time.camera_captured_file_path = None
            fields_updated.append("camera_captured_file")

        equipment_time.last_modified_at = now
        equipment_time.last_modified_by = current_rsrc_no
        db.add(equipment_time)
        db.commit()
        db.refresh(equipment_time)

        documents = (
            db.query(AdditionalDocuments)
            .filter(
                AdditionalDocuments.equipment_time_id == equipment_time.id,
                AdditionalDocuments.is_archived == False
            )
            .all()
        )
        equipment_time_data = serialize_equipment_time_with_documents(equipment_time, documents)

        message = (
            f"Equipment time updated successfully. Fields updated: {', '.join(fields_updated)}"
            if fields_updated
            else "No changes provided. Equipment time data remains unchanged."
        )

        logger.info(f"Equipment time {equipment_time_id} updated successfully for job {equipment_time.job_no}")
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": message,
                "success": True,
                "result": equipment_time_data
            },
            status_code=status.HTTP_200_OK
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error updating equipment_time {equipment_time_id}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to update equipment_time: {str(e)}",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



async def delete_equipment_time(equipment_time_id: int, db: Session) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')
        now = get_timezone_now()

        equipment_time = (
            db.query(EquipmentTime)
            .join(Jobs, EquipmentTime.job_no == Jobs.job_no)
            .join(JobsTasks, JobsTasks.job_no == Jobs.job_no)
            .filter(
                EquipmentTime.id == equipment_time_id,
                EquipmentTime.is_archived == False,
                Jobs.is_archived == False,
                JobsTasks.rsrc_no == current_rsrc_no,
                JobsTasks.is_archived == False
            )
            .first()
        )

        if not equipment_time:
            logger.error(f"Equipment time with ID {equipment_time_id} not found or access denied")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Equipment time with ID {equipment_time_id} not found or access denied",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Archive associated documents and remove their stored files.
        documents = (
            db.query(AdditionalDocuments)
            .filter(
                AdditionalDocuments.equipment_time_id == equipment_time_id,
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

        delete_stored_file_if_exists(equipment_time.camera_captured_file_path, "camera_captured_file")
        equipment_time.camera_captured_file_name = None
        equipment_time.camera_captured_file_path = None

        equipment_time.is_archived = True
        equipment_time.last_modified_at = now
        equipment_time.last_modified_by = current_rsrc_no
        db.add(equipment_time)
        db.commit()

        logger.info(f"Equipment time {equipment_time_id} and associated documents deleted successfully")
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": f"Equipment time with ID {equipment_time_id} deleted successfully",
                "success": True,
                "result": {}
            },
            status_code=status.HTTP_200_OK
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting equipment_time {equipment_time_id}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to delete equipment_time: {str(e)}",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
