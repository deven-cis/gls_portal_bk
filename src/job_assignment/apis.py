from fastapi import status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import update
from src.core.logger import logger
from src.job_assignment.models import JobAssignment
from src.job_assignment.schema import JobReassignRequestSchema
from src.resources.models import Resources
from src.jobs_tasks.models import JobsTasks
from src.cases.models import Cases
from src.core.context import get_context
from src.core.timezone_utils import get_timezone_now


async def reassign_job_service(payload: JobReassignRequestSchema, db: Session) -> JSONResponse:
    try:
        # Lazy imports to prevent circular imports
        from src.jobs.models import Jobs, JobStatusEnum
        
        current_rsrc_no = get_context('rsrc_no')
        now = get_timezone_now()
        job_no = payload.job_id
        assignee_rsrc_no = payload.assignee_rsrc_no

        logger.info(f"Reassigning job {job_no} from rsrc {current_rsrc_no} to rsrc {assignee_rsrc_no}")

        # Validate job exists and current resource has access
        job = (
            db.query(Jobs)
            .join(JobsTasks, JobsTasks.job_no == Jobs.job_no)
            .join(Cases, Cases.case_no == Jobs.case_no)
            .filter(
                Jobs.job_no == job_no,
                Jobs.is_archived == False,
                Cases.is_archived == False,
                JobsTasks.rsrc_no == current_rsrc_no,
                JobsTasks.is_archived == False
            )
            .first()
        )

        if not job:
            logger.warning(f"Job {job_no} not found or access denied for rsrc {current_rsrc_no}")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Job not found or access denied",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Validate assignee resource exists
        assignee = (
            db.query(Resources.rsrc_no)
            .filter(
                Resources.rsrc_no == assignee_rsrc_no,
                Resources.is_archived == False
            )
            .first()
        )

        if not assignee:
            logger.warning(f"Assignee resource {assignee_rsrc_no} not found")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Assignee resource not found",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Archive existing assignments for any active tasks under this job
        db.execute(
            update(JobAssignment)
            .where(
                JobAssignment.job_task_no.in_(
                    db.query(JobsTasks.task_no).filter(
                        JobsTasks.job_no == job_no,
                        JobsTasks.is_archived == False,
                    )
                ),
                JobAssignment.is_archived == False,
            )
            .values(
                is_archived=True,
                last_modified_by=current_rsrc_no,
                last_modified_at=now,
            )
        )

        # Find a primary active task for this job to record in JobAssignment
        primary_task = (
            db.query(JobsTasks)
            .filter(
                JobsTasks.job_no == job_no,
                JobsTasks.is_archived == False,
            )
            .order_by(JobsTasks.task_no.asc())
            .first()
        )

        if not primary_task:
            logger.warning(f"No active tasks found for job {job_no} to assign")
            db.rollback()
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "No active tasks found for job",
                    "success": False,
                    "result": {},
                },
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # Create new assignment at task level, tracked by job_no context
        assignment = JobAssignment(
            assigner_id=current_rsrc_no,
            assignee_id=assignee_rsrc_no,
            job_task_no=primary_task.task_no,
            case_no=job.case_no,
            reason=payload.reason,
            entered_by=current_rsrc_no,
            last_modified_by=current_rsrc_no,
            last_modified_at=now,
            entered_at=now,
        )
        db.add(assignment)

        # Reset job status
        db.execute(
            update(Jobs)
            .where(
                Jobs.job_no == job_no,
                Jobs.is_archived == False
            )
            .values(
                computed_status=JobStatusEnum.SESSION_NOT_STARTED.value,
                actual_session_start_time=None,
                actual_session_end_time=None,
                session_duration=None,
                session_completed=False,
                last_modified_by=current_rsrc_no,
                last_modified_at=now
            )
        )

        # Update JobsTasks rsrc_no to new assignee
        db.execute(
            update(JobsTasks)
            .where(
                JobsTasks.job_no == job_no,
                JobsTasks.is_archived == False
            )
            .values(
                rsrc_no=assignee_rsrc_no,
                last_modified_by=current_rsrc_no,
                last_modified_at=now
            )
        )

        db.commit()
        db.refresh(assignment)

        logger.info(f"Job {job_no} successfully reassigned from rsrc {current_rsrc_no} to rsrc {assignee_rsrc_no}")

        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Job reassigned successfully",
                "success": True,
                "result": {
                    "job_no": job_no,
                    "previous_owner": current_rsrc_no,
                    "new_owner": assignee_rsrc_no,
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