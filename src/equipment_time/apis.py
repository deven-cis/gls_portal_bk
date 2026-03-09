from typing import List, Optional
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from fastapi import HTTPException, status, UploadFile, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from src.equipment_time.models import EquipmentTime
from src.equipment_time.schema import (
    EquipmentTimeSchema,
    EquipmentTimeWithDocumentsSchema,
    AdditionalDocumentResponseSchema,
)
from src.additional_documents.models import AdditionalDocuments
from src.core.file_utils import save_multiple_files, save_image_file
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
            logger.error(f"Equipment time for job_no {job_no} not found or access denied")
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

        documents_data = [
            AdditionalDocumentResponseSchema.model_validate(doc).model_dump()
            for doc in documents
        ]

        equipment_time_with_docs = EquipmentTimeWithDocumentsSchema(
            id=equipment_time.id,
            job_no=equipment_time.job_no,
            laptop_used=equipment_time.laptop_used,
            pip_used=equipment_time.pip_used,
            exhibit_tech=equipment_time.exhibit_tech,
            parking_cost=str(equipment_time.parking_cost) if equipment_time.parking_cost else "0.00",
            time_after=str(equipment_time.time_after) if equipment_time.time_after else None,
            camera_captured_file_name=equipment_time.camera_captured_file_name,
            camera_captured_file_path=equipment_time.camera_captured_file_path,
            documents=documents_data
        )

        logger.info(
            f"Successfully retrieved equipment_time for job {job_no} "
            f"(equipment_time_id: {equipment_time.id}) with {len(documents_data)} document(s)"
        )

        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": f"Equipment time for job {job_no} found with {len(documents_data)} document(s)",
                "success": True,
                "result": equipment_time_with_docs.model_dump()
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

        # Handle camera file upload
        camera_captured_file_name, camera_captured_file_path = (
            await save_image_file(camera_captured_file, "equipment_time")
            if camera_captured_file and camera_captured_file.filename
            else (None, None)
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
            "camera_captured_file_name": camera_captured_file_name,
            "camera_captured_file_path": camera_captured_file_path,
            "entered_by": current_rsrc_no,
            "entered_at": now,
            "last_modified_by": current_rsrc_no,
            "last_modified_at": now
        }
        for key, value in equipment_payload.items():
            setattr(equipment_time, key, value)

        db.add(equipment_time)
        db.flush()  # get equipment_time.id before commit

        # Handle additional documents
        documents_created = 0
        valid_files = [f for f in files if f and f.filename] if files else []
        if valid_files:
            saved_files = await save_multiple_files(valid_files, "equipment_time")
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
        documents_data = [
            AdditionalDocumentResponseSchema.model_validate(doc).model_dump()
            for doc in db.query(AdditionalDocuments).filter(
                AdditionalDocuments.equipment_time_id == equipment_time.id,
                AdditionalDocuments.is_archived == False
            ).all()
        ]

        equipment_time_with_docs = EquipmentTimeWithDocumentsSchema(
            id=equipment_time.id,
            job_no=equipment_time.job_no,
            laptop_used=equipment_time.laptop_used,
            pip_used=equipment_time.pip_used,
            exhibit_tech=equipment_time.exhibit_tech,
            parking_cost=str(equipment_time.parking_cost) if equipment_time.parking_cost else "0.00",
            time_after=str(equipment_time.time_after) if equipment_time.time_after else None,
            camera_captured_file_name=equipment_time.camera_captured_file_name,
            camera_captured_file_path=equipment_time.camera_captured_file_path,
            documents=documents_data
        )

        message = f"Equipment time created successfully with {documents_created} document(s)" if documents_created else "Equipment time created successfully"
        logger.info(f"Equipment time created for job {job_no} with {documents_created} document(s)")

        return JSONResponse(
            content={
                "status_code": status.HTTP_201_CREATED,
                "message": message,
                "success": True,
                "result": equipment_time_with_docs.model_dump()
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

        # Helper to delete file safely
        def delete_file_if_exists(file_path: Optional[str], label: str):
            if file_path:
                try:
                    path = Path(file_path)
                    if path.exists():
                        path.unlink()
                        logger.info(f"Deleted {label}: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete {label} {file_path}: {str(e)}")

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
                    delete_file_if_exists(doc.file_path, "document")
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
            saved_files = await save_multiple_files(valid_files, "equipment_time")
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
            delete_file_if_exists(equipment_time.camera_captured_file_path, "camera_captured_file")
            if camera_captured_file and camera_captured_file.filename:
                equipment_time.camera_captured_file_name, equipment_time.camera_captured_file_path = (
                    await save_image_file(camera_captured_file, "equipment_time")
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

        equipment_time_data = EquipmentTimeSchema(
            id=equipment_time.id,
            job_no=equipment_time.job_no,
            laptop_used=equipment_time.laptop_used,
            pip_used=equipment_time.pip_used,
            exhibit_tech=equipment_time.exhibit_tech,
            parking_cost=str(equipment_time.parking_cost) if equipment_time.parking_cost else "0.00",
            time_after=str(equipment_time.time_after) if equipment_time.time_after else None
        )

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
                "result": equipment_time_data.model_dump()
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

        # Archive associated documents
        db.query(AdditionalDocuments).filter(
            AdditionalDocuments.equipment_time_id == equipment_time_id,
            AdditionalDocuments.is_archived == False
        ).update(
            {
                "is_archived": True,
                "last_modified_at": now,
                "last_modified_by": current_rsrc_no
            },
            synchronize_session=False
        )

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