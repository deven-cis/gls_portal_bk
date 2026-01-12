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
from src.core.file_utils import save_multiple_files
from src.core.logger import logger
from src.core.context import get_context


async def get_equipment_time_by_job(job_no: int, db: Session) -> JSONResponse:
    try:
        equipment_time = db.query(EquipmentTime).filter(
            EquipmentTime.job_no == job_no,
            EquipmentTime.is_archived == False
        ).first()
        
        if not equipment_time:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Equipment time for job_no {job_no} not found",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        documents = db.query(AdditionalDocuments).filter(
            AdditionalDocuments.equipment_time_id == equipment_time.id,
            AdditionalDocuments.is_archived == False
        ).all()
        
        logger.info(
            f"Found {len(documents)} document(s) for equipment_time_id {equipment_time.id}, job_no {job_no}"
        )
        
        documents_data = [
            AdditionalDocumentResponseSchema.model_validate(doc).model_dump()
            for doc in documents
        ]
        
        logger.info(f"Serialized {len(documents_data)} document(s) successfully")
        
        time_after_str = None
        if equipment_time.time_after:
            time_after_str = str(equipment_time.time_after)
        
        parking_cost_str = str(equipment_time.parking_cost) if equipment_time.parking_cost else "0.00"
        
        equipment_time_with_docs = EquipmentTimeWithDocumentsSchema(
            id=equipment_time.id,
            job_no=equipment_time.job_no,
            laptop_used=equipment_time.laptop_used,
            pip_used=equipment_time.pip_used,
            exhibit_tech=equipment_time.exhibit_tech,
            parking_cost=parking_cost_str,
            time_after=time_after_str,
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
) -> JSONResponse:
    try:
        logger.info(f"Creating equipment_time for files: {files}")
        from src.jobs.models import Jobs
        job = db.query(Jobs).filter(Jobs.job_no == job_no).first()
        if not job:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Job with job_no {job_no} not found",
                    "success": False,
                    "result": []
                },
                status_code=status.HTTP_404_NOT_FOUND,
            )
        
        parking_cost_decimal = Decimal(parking_cost) if parking_cost else Decimal('0.00')
        
        equipment_time = EquipmentTime(
            job_no=job_no,
            laptop_used=laptop_used,
            pip_used=pip_used,
            exhibit_tech=exhibit_tech,
            parking_cost=parking_cost_decimal,
            time_after=time_after
        )
        
        equipment_time.save()
        
        logger.info(f"Created equipment_time with id={equipment_time.id} for job_no={job_no}")
        
        documents_created = 0
        logger.info(f"Files received: {files is not None}, Count: {len(files) if files else 0}")
        
        if files and len(files) > 0:
            try:
                valid_files = [f for f in files if f and f.filename]
                logger.info(f"Valid files to save: {len(valid_files)}")
                
                if valid_files:
                    saved_files = await save_multiple_files(valid_files, "equipment_time")
                    logger.info(f"Saving {len(saved_files)} file(s) for equipment_time_id {equipment_time.id}")
                    
                    for file_name, file_path in saved_files:
                        try:
                            doc = AdditionalDocuments(
                                job_no=job_no,
                                equipment_time_id=equipment_time.id,
                                file_name=file_name,
                                file_path=file_path,
                            )
                            doc.save()
                            documents_created += 1
                            logger.info(f"Successfully saved document: id={doc.id}, file_name={file_name}, file_path={file_path}, equipment_time_id={equipment_time.id}")
                        except Exception as doc_error:
                            logger.error(f"Error saving document {file_name}: {str(doc_error)}", exc_info=True)
                            continue
                else:
                    logger.warning("No valid files found in files list")
            except Exception as file_error:
                logger.error(f"Error processing files: {str(file_error)}", exc_info=True)
        else:
            logger.info("No files provided for equipment_time creation")
        
        created_documents = db.query(AdditionalDocuments).filter(
            AdditionalDocuments.equipment_time_id == equipment_time.id,
            AdditionalDocuments.is_archived == False
        ).all()
        
        logger.info(f"Found {len(created_documents)} document(s) in database for equipment_time_id {equipment_time.id}")
        
        documents_data = [
            AdditionalDocumentResponseSchema.model_validate(doc).model_dump()
            for doc in created_documents
        ]
        
        time_after_str = None
        if equipment_time.time_after:
            time_after_str = str(equipment_time.time_after)
        
        parking_cost_str = str(equipment_time.parking_cost) if equipment_time.parking_cost else "0.00"
        
        equipment_time_with_docs = EquipmentTimeWithDocumentsSchema(
            id=equipment_time.id,
            job_no=equipment_time.job_no,
            laptop_used=equipment_time.laptop_used,
            pip_used=equipment_time.pip_used,
            exhibit_tech=equipment_time.exhibit_tech,
            parking_cost=parking_cost_str,
            time_after=time_after_str,
            documents=documents_data
        )
        
        message = "Equipment time created successfully"
        if documents_created:
            message += f" with {documents_created} document(s)"
        
        logger.info(f"Returning equipment_time with {len(documents_data)} document(s) in response")
        
        return JSONResponse(
            content={
                "status_code": status.HTTP_201_CREATED,
                "message": message,
                "success": True,
                "result": equipment_time_with_docs.model_dump(),
            },
            status_code=status.HTTP_201_CREATED,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating equipment_time for job {job_no}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to create equipment_time: {str(e)}",
                "success": False,
                "result": [],
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
) -> JSONResponse:
    try:
        equipment_time = db.query(EquipmentTime).filter(
            EquipmentTime.id == equipment_time_id,
            EquipmentTime.is_archived == False
        ).first()
        
        if not equipment_time:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Equipment time with ID {equipment_time_id} not found",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        fields_updated = []
        
        if laptop_used is not None:
            equipment_time.laptop_used = laptop_used.lower() in ['true', '1', 'yes']
            fields_updated.append("laptop_used")
        
        if pip_used is not None:
            equipment_time.pip_used = pip_used.lower() in ['true', '1', 'yes']
            fields_updated.append("pip_used")
        
        if exhibit_tech is not None:
            equipment_time.exhibit_tech = exhibit_tech.lower() in ['true', '1', 'yes']
            fields_updated.append("exhibit_tech")
        
        if parking_cost is not None:
            try:
                equipment_time.parking_cost = Decimal(parking_cost) if parking_cost else Decimal('0.00')
                fields_updated.append("parking_cost")
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid parking_cost value: {parking_cost}, error: {str(e)}")
        
        if time_after is not None:
            if isinstance(time_after, str):
                equipment_time.time_after = time_after.strip() if time_after.strip() else time_after
            else:
                equipment_time.time_after = time_after
            fields_updated.append("time_after")
        
        form_data = await request.form()
        remove_documents = form_data.getlist("remove_documents") if "remove_documents" in form_data else []
        
        documents_removed = 0
        if remove_documents:
            for doc_id_str in remove_documents:
                try:
                    doc_id = int(doc_id_str)
                    doc = db.query(AdditionalDocuments).filter(
                        AdditionalDocuments.id == doc_id,
                        AdditionalDocuments.equipment_time_id == equipment_time_id,
                        AdditionalDocuments.is_archived == False
                    ).first()
                    
                    if doc:
                        if doc.file_path:
                            try:
                                file_path = Path(doc.file_path)
                                if file_path.exists():
                                    file_path.unlink()
                                    logger.info(f"Deleted file: {doc.file_path}")
                            except Exception as e:
                                logger.warning(f"Failed to delete file {doc.file_path}: {str(e)}")
                        
                        doc.is_archived = True
                        doc.save()
                        documents_removed += 1
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid document ID: {doc_id_str}, error: {str(e)}")
                    continue
        
        if documents_removed > 0:
            fields_updated.append(f"documents (removed {documents_removed})")
        
        documents_uploaded = 0
        if files:
            saved_files = await save_multiple_files(files, "equipment_time")
            logger.info(f"Uploading {len(saved_files)} file(s) for equipment_time_id {equipment_time.id}")
            entered_by = get_context('entered_by') or 0
            for file_name, file_path in saved_files:
                doc = AdditionalDocuments(
                    job_no=equipment_time.job_no,
                    equipment_time_id=equipment_time.id,
                    file_name=file_name,
                    file_path=file_path,
                    entered_by=entered_by,
                    last_modified_by=entered_by,
                    entered_at=datetime.now(),
                    last_modified_at=datetime.now(),
                )
                db.add(doc)
                db.commit()
                db.refresh(doc)
                documents_uploaded += 1
                logger.info(f"Uploaded document: id={doc.id}, file_name={file_name}, equipment_time_id={equipment_time.id}")
        
        if documents_uploaded > 0:
            fields_updated.append(f"documents (uploaded {documents_uploaded})")
        
        equipment_time.save()
        
        time_after_str = None
        if equipment_time.time_after:
            time_after_str = str(equipment_time.time_after)
        
        parking_cost_str = str(equipment_time.parking_cost) if equipment_time.parking_cost else "0.00"
        
        equipment_time_data = EquipmentTimeSchema(
            id=equipment_time.id,
            job_no=equipment_time.job_no,
            laptop_used=equipment_time.laptop_used,
            pip_used=equipment_time.pip_used,
            exhibit_tech=equipment_time.exhibit_tech,
            parking_cost=parking_cost_str,
            time_after=time_after_str
        )
        
        if fields_updated:
            message = f"Equipment time updated successfully. Fields updated: {', '.join(fields_updated)}"
        else:
            message = "No changes provided. Equipment time data remains unchanged."
        
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": message,
                "success": True,
                "result": equipment_time_data.model_dump()
            },
            status_code=status.HTTP_200_OK
        )
    except HTTPException:
        raise
    except Exception as e:
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
        equipment_time = db.query(EquipmentTime).filter(
            EquipmentTime.id == equipment_time_id,
            EquipmentTime.is_archived == False
        ).first()
        
        if not equipment_time:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Equipment time with ID {equipment_time_id} not found",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        equipment_time.is_archived = True
        equipment_time.save()
        
        logger.info(f"Successfully deleted equipment_time {equipment_time_id}")
        
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
