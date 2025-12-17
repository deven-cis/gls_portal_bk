from typing import List, Optional
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
    Query,
    Request,
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.auth.utils import get_current_user
from src.billings.models import Billings
from src.billings.schema import BillingCreateSchema, BillingUpdateSchema, BillingSchema, BillingWithDocumentsSchema, AdditionalDocumentResponseSchema
from src.jobs.models import Jobs
from src.additional_documents.models import AdditionalDocuments
from src.core.file_utils import save_multiple_files
from src.core.logger import logger
from src.core.database import get_db


billings_router = APIRouter(prefix="/billings", tags=["billings"])


@billings_router.get("/get/{job_no}", status_code=200)
async def get_billing_by_job(
    job_no: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Get billing for a specific job with all associated documents.
    Most common use case - frontend passes job_no to get billing info.
    Returns complete billing information including all uploaded documents.
    """
    try:
        billing = db.query(Billings).filter(
            Billings.job_no == job_no,
            Billings.is_archived == False
        ).first()
        
        if not billing:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Billing for job_no {job_no} not found",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Get all associated additional documents for this billing
        documents = db.query(AdditionalDocuments).filter(
            AdditionalDocuments.billing_id == billing.id,
            AdditionalDocuments.is_archived == False
        ).all()
        
        # Serialize documents
        documents_data = [
            AdditionalDocumentResponseSchema.model_validate(doc).model_dump()
            for doc in documents
        ]
        
        # Create complete billing response with documents
        billing_with_docs = BillingWithDocumentsSchema(
            id=billing.id,
            job_no=billing.job_no,
            cancel_en_route=billing.cancel_en_route,
            cancel_setup=billing.cancel_setup,
            billing_notes=billing.billing_notes,
            videographer_hours_present=billing.videographer_hours_present,
            file_hours_length=billing.file_hours_length,
            documents=documents_data
        )
        
        logger.info(f"Successfully retrieved billing for job {job_no} (billing_id: {billing.id}) with {len(documents_data)} document(s)")
        
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": f"Billing for job {job_no} found with {len(documents_data)} document(s)",
                "success": True,
                "result": billing_with_docs.model_dump()
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


@billings_router.post("/create", status_code=201)
async def create_billing(
    job_no: int = Form(...),
    cancel_en_route: bool = Form(False),
    cancel_setup: bool = Form(False),
    billing_notes: Optional[str] = Form(None),
    videographer_hours_present: Optional[str] = Form(None),
    file_hours_length: Optional[str] = Form(None),
    files: List[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Create billing for a job.

    - Associates billing with a job via job_no
    - Supports optional additional documents (multiple files)
    - Returns structured JSON with status_code, message, success, result
    """
    try:
        logger.info(f"Creating billing for files: {files}")
        job = db.query(Jobs).filter(Jobs.job_no == job_no).first()
        if not job:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Job with job_no {job_no} not found",
                    "success": False,
                    "result": [],
                },
                status_code=status.HTTP_404_NOT_FOUND,
            )

        billing = Billings(
            job_no=job_no,
            cancel_en_route=cancel_en_route,
            cancel_setup=cancel_setup,
            billing_notes=billing_notes,
            videographer_hours_present=videographer_hours_present,
            file_hours_length=file_hours_length,
        )
        billing = Billings.save(billing)

        # Handle multiple additional documents
        documents_created = 0
        if files:
            saved_files = await save_multiple_files(files, "billings")
            for file_name, file_path in saved_files:
                doc = AdditionalDocuments(
                    job_no=job_no,
                    billing_id=billing.id,
                    file_name=file_name,
                    file_path=file_path,
                )
                AdditionalDocuments.save(doc)
                documents_created += 1

        billing_data = BillingSchema.model_validate(billing)

        message = "Billing created successfully"
        if documents_created:
            message += f" with {documents_created} document(s)"

        return JSONResponse(
            content={
                "status_code": status.HTTP_201_CREATED,
                "message": message,
                "success": True,
                "result": billing_data.model_dump(),
            },
            status_code=status.HTTP_201_CREATED,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating billing for job {job_no}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to create billing: {str(e)}",
                "success": False,
                "result": [],
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@billings_router.put("/update/{billing_id}", status_code=200)
async def update_billing(
    billing_id: int,
    request: Request,
    job_no: Optional[int] = Form(None),
    cancel_en_route: Optional[str] = Form(None),
    cancel_setup: Optional[str] = Form(None),
    billing_notes: Optional[str] = Form(None),
    videographer_hours_present: Optional[str] = Form(None),
    file_hours_length: Optional[str] = Form(None),
    files: List[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Update billing. Only provided fields will be updated, others remain unchanged.
    Frontend sends: job_no, cancel_en_route, cancel_setup, billing_notes,
    videographer_hours_present, file_hours_length, files (new uploads), remove_documents (IDs to remove)
    """
    try:
        logger.info(f"Updating billing for files: {files}")
        billing = db.query(Billings).filter(
            Billings.id == billing_id,
            Billings.is_archived == False
        ).first()
        
        if not billing:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Billing with ID {billing_id} not found",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Track which fields were updated
        fields_updated = []
        
        # Update only fields that are provided (not None)
        if job_no is not None:
            # Verify job exists
            job = db.query(Jobs).filter(Jobs.job_no == job_no).first()
            if not job:
                return JSONResponse(
                    content={
                        "status_code": status.HTTP_404_NOT_FOUND,
                        "message": f"Job with job_no {job_no} not found",
                        "success": False,
                        "result": {}
                    },
                    status_code=status.HTTP_404_NOT_FOUND
                )
            billing.job_no = job_no
            fields_updated.append("job_no")
        
        if cancel_en_route is not None:
            # Convert string to boolean
            billing.cancel_en_route = cancel_en_route.lower() in ['true', '1', 'yes']
            fields_updated.append("cancel_en_route")
        
        if cancel_setup is not None:
            # Convert string to boolean
            billing.cancel_setup = cancel_setup.lower() in ['true', '1', 'yes']
            fields_updated.append("cancel_setup")
        
        if billing_notes is not None:
            if isinstance(billing_notes, str):
                billing.billing_notes = billing_notes.strip() if billing_notes.strip() else billing_notes
            else:
                billing.billing_notes = billing_notes
            fields_updated.append("billing_notes")
        
        if videographer_hours_present is not None:
            if isinstance(videographer_hours_present, str):
                billing.videographer_hours_present = videographer_hours_present.strip() if videographer_hours_present.strip() else videographer_hours_present
            else:
                billing.videographer_hours_present = videographer_hours_present
            fields_updated.append("videographer_hours_present")
        
        if file_hours_length is not None:
            if isinstance(file_hours_length, str):
                billing.file_hours_length = file_hours_length.strip() if file_hours_length.strip() else file_hours_length
            else:
                billing.file_hours_length = file_hours_length
            fields_updated.append("file_hours_length")
        
        # Handle document removal - read from form data to get all values with same key
        form_data = await request.form()
        remove_documents = form_data.getlist("remove_documents") if "remove_documents" in form_data else []
        
        documents_removed = 0
        if remove_documents:
            for doc_id_str in remove_documents:
                try:
                    doc_id = int(doc_id_str)
                    doc = db.query(AdditionalDocuments).filter(
                        AdditionalDocuments.id == doc_id,
                        AdditionalDocuments.billing_id == billing_id,
                        AdditionalDocuments.is_archived == False
                    ).first()
                    
                    if doc:
                        # Delete physical file if exists
                        if doc.file_path:
                            try:
                                file_path = Path(doc.file_path)
                                if file_path.exists():
                                    file_path.unlink()
                                    logger.info(f"Deleted file: {doc.file_path}")
                            except Exception as e:
                                logger.warning(f"Failed to delete file {doc.file_path}: {str(e)}")
                        
                        # Archive the document
                        doc.is_archived = True
                        doc.save()
                        documents_removed += 1
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid document ID: {doc_id_str}, error: {str(e)}")
                    continue
        
        if documents_removed > 0:
            fields_updated.append(f"documents (removed {documents_removed})")
        
        # Handle new document uploads
        documents_uploaded = 0
        if files:
            saved_files = await save_multiple_files(files, "billings")
            for file_name, file_path in saved_files:
                doc = AdditionalDocuments(
                    job_no=billing.job_no,
                    billing_id=billing.id,
                    file_name=file_name,
                    file_path=file_path,
                )
                AdditionalDocuments.save(doc)
                documents_uploaded += 1
        
        if documents_uploaded > 0:
            fields_updated.append(f"documents (uploaded {documents_uploaded})")
        
        # Save billing changes
        billing.save()
        
        # Serialize SQLAlchemy model to Pydantic schema
        billing_data = BillingSchema.model_validate(billing)
        
        # Prepare response message
        if fields_updated:
            message = f"Billing updated successfully. Fields updated: {', '.join(fields_updated)}"
        else:
            message = "No changes provided. Billing data remains unchanged."
        
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": message,
                "success": True,
                "result": billing_data.model_dump()
            },
            status_code=status.HTTP_200_OK
        )
    except HTTPException:
        raise
    except Exception as e:
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



@billings_router.delete("/delete/{billing_id}", status_code=200)
async def delete_billing(
    billing_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        billing = db.query(Billings).filter(Billings.id == billing_id, Billings.is_archived == False).first()
        if not billing or billing.is_archived:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Billing with ID {billing_id} not found",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        billing.is_archived = True
        billing.save()
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": f"Billing with ID {billing_id} deleted successfully",
                "success": True,
                "result": {}
            },
            status_code=status.HTTP_200_OK
        )
    except HTTPException:
        raise
    except Exception as e:
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
