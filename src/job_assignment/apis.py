from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import update

from src.auth.utils import get_current_user
from src.core.database import get_db
from src.core.logger import logger
from src.job_assignment.models import JobAssignment
from src.job_assignment.schema import JobReassignRequestSchema, JobAssignmentResponseSchema
from src.jobs.models import Jobs
from src.users.models import Users
from src.witnesses.models import Witnesses
from src.witness_videos.models import WitnessVideos
from src.attorneys.models import Attorneys
from src.billings.models import Billings
from src.equipment_time.models import EquipmentTime
from src.additional_documents.models import AdditionalDocuments
from src.core.context import get_context


job_assignment_apis = APIRouter(prefix='/jobs', tags=['jobs'])


@job_assignment_apis.post("/reassign", status_code=200)
async def reassign_job(
    payload: JobReassignRequestSchema,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    """
    Reassign a job to another user.
    Updates entered_by for all related records (witnesses, videos, attorneys, etc.)
    """
    try:
        logger.info(f"Reassigning job {payload.job_id} to user {payload.assignee_user_id}, {payload}")
        current_entered_by = get_context('entered_by')
        current_user_id = get_context('user_id')
        # Get the job
        job = db.query(Jobs).filter(
            Jobs.job_no == payload.job_id,
            Jobs.entered_by == current_entered_by,
            Jobs.is_archived == False
        ).first()
        logger.info(f"Job: {job}")
        if not job:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Job not found",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        assignee_user_id = payload.assignee_user_id
        job_no = payload.job_id
        assignee_entered_by = payload.assignee_entered_by
        
        # Create JobAssignment record
        assignment = JobAssignment(
            assigner_id=current_user_id,
            assignee_id=assignee_user_id,
            job_no=job_no,
            case_no=job.case_no,
            reason=payload.reason,
            entered_by=current_user_id,
            last_modified_by=current_user_id
        )
        db.add(assignment)
        logger.info(f"Assignment: {assignment}")
        
        # Update entered_by for all related tables in bulk
        tables_to_update = [
            (Jobs, Jobs.job_no),
            (Witnesses, Witnesses.job_no),
            (WitnessVideos, WitnessVideos.job_no),
            (Attorneys, Attorneys.job_no),
            (Billings, Billings.job_no),
            (EquipmentTime, EquipmentTime.job_no),
            (AdditionalDocuments, AdditionalDocuments.job_no),
        ]
        
        for model, job_no_column in tables_to_update:
            db.execute(
                update(model)
                .where(job_no_column == job_no, model.is_archived == False)
                .values(entered_by=assignee_entered_by, last_modified_by=assignee_entered_by)
            )
        
        db.commit()
        db.refresh(assignment)
        
        logger.info(f"Job {job_no} reassigned from user {current_entered_by} to user {assignee_entered_by}")
        logger.info(f"Assignment: {assignment}")
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Job reassigned successfully",
                "success": True,
                "result": []
            },
            status_code=status.HTTP_200_OK
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error reassigning job: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to reassign job: {str(e)}",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
