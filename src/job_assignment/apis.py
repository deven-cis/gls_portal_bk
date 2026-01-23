from fastapi import status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import update
from src.core.logger import logger
from src.job_assignment.models import JobAssignment
from src.job_assignment.schema import JobReassignRequestSchema
from src.jobs.models import Jobs
from src.witnesses.models import Witnesses
from src.witness_videos.models import WitnessVideos
from src.attorneys.models import Attorneys
from src.billings.models import Billings
from src.equipment_time.models import EquipmentTime
from src.additional_documents.models import AdditionalDocuments
from src.core.context import get_context
from src.users.models import Users

async def reassign_job_service(payload: JobReassignRequestSchema, db: Session) -> JSONResponse:
    try:
        current_user_id = get_context('user_id')
        current_user_no = get_context('entered_by')
        
        assignee_user_id = payload.assignee_user_id
        job_no = payload.job_id
        
        logger.info(
            f"Reassigning job {job_no}: "
            f"from user_id={current_user_id} (user_no={current_user_no}) "
            f"to user_id={assignee_user_id}"
        )

        job = db.query(Jobs).filter(
            Jobs.job_no == job_no,
            Jobs.entered_by == current_user_no,
            Jobs.is_archived == False
        ).first()

        if not job:
            logger.warning(f"Job {job_no} not found or access denied for user {current_user_no}")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Job not found or you don't have permission to reassign it",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )

        assignee_user = db.query(Users).filter(
            Users.id == assignee_user_id,
            Users.is_archived == False
        ).first()

        if not assignee_user:
            logger.warning(f"Assignee user {assignee_user_id} not found")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Assignee user not found",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        assignee_user_no = assignee_user.user_no
            
        db.execute(
            update(JobAssignment)
            .where(
                JobAssignment.job_no == job_no,
                JobAssignment.is_archived == False
            )
            .values(
                is_archived=True,
                last_modified_by=current_user_id
            )
        )
        
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
        
        db.execute(
            update(Jobs)
            .where(
                Jobs.job_no == job_no,
                Jobs.is_archived == False
            )
            .values(
                entered_by=assignee_user_no,
                last_modified_by=assignee_user_no,
                computed_status="upcoming",
                actual_session_start_time=None,
                actual_session_end_time=None,
                session_duration=None,
                session_completed=False
            )
        )
        
        related_models = [
            Witnesses,
            WitnessVideos,
            Attorneys,
            Billings,
            EquipmentTime,
            AdditionalDocuments
        ]
        
        for model in related_models:
            db.execute(
                update(model)
                .where(
                    model.job_no == job_no,
                    model.is_archived == False
                )
                .values(
                    entered_by=assignee_user_no,
                    last_modified_by=assignee_user_no
                )
            )
        
        db.commit()
        
        logger.info(
            f"Job {job_no} successfully reassigned "
            f"from user_no {current_user_no} to user_no {assignee_user_no}"
        )
        
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Job reassigned successfully",
                "success": True,
                "result": {
                    "job_no": job_no,
                    "previous_owner": current_user_no,
                    "new_owner": assignee_user_no,
                    "assignment_id": assignment.id
                }
            },
            status_code=status.HTTP_200_OK
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error reassigning job {payload.job_id}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to reassign job: {str(e)}",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
