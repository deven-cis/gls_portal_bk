from typing import List, Optional, Union
from datetime import datetime, timedelta, date
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy import func, String
from sqlalchemy.orm import Session, joinedload, with_loader_criteria
import subprocess
import tempfile
import os
from pathlib import Path
from src.jobs_tasks.models import JobsTasks
from src.jobs.models import Jobs
from src.core.logger import logger
from src.cases.models import Cases
from src.core.context import get_context
from src.jobs_tasks.schema import (
    JobsTaskSchema, 
    JobsTaskCancelSchema, 
    JobsTaskDetailsSchema, 
    MarkJobsTaskAsDoneSchema,
    JobsTaskListSchema,
    JobsTaskCalendarSchema,
    JobsTaskCancelledAndCompletedSchema,
    JobsTaskCompletedDetailsSchema
)
from src.jobs.models import JobStatusEnum, CancelReasonEnum
from src.jobs_tasks.utils import (
    jobstask_to_calendar_event,
    get_date_range_for_month,
    get_date_range_for_week,
    get_video_upload_status
)
from src.witnesses.models import Witnesses
from src.witness_videos.models import WitnessVideos
from src.attorneys.models import Attorneys
from src.witnesses.schema import WitnessSchema
from src.attorneys.schema import AttorneySchema
from src.core.timezone_utils import get_timezone_now

async def get_cancelled_jobstask_details(
    job_no: int,
    current_user: dict,
    db: Session
) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')
        logger.info(f"Getting cancelled jobstask details for job_no {job_no} for user {current_rsrc_no}")

        result = (
            db.query(
                Jobs.job_no,
                Jobs.cancel_reason,
                Jobs.cancel_details
            )
            .join(JobsTasks, JobsTasks.job_no == Jobs.job_no)
            .join(Cases, Cases.case_no == Jobs.case_no)
            .filter(
                Jobs.job_no == job_no,
                Jobs.is_archived == False,
                Cases.is_archived == False,
                JobsTasks.is_archived == False,
                JobsTasks.rsrc_no == current_rsrc_no,
                Jobs.computed_status == JobStatusEnum.CANCELLED.value
            )
            .first()
        )

        if not result:
            logger.error(f"Job with job_no {job_no} not found, not cancelled, or access denied")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Job with job_no {job_no} not found, not cancelled, or access denied",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )

        cancel_reason = (
            result.cancel_reason.value
            if isinstance(result.cancel_reason, CancelReasonEnum)
            else result.cancel_reason
        )

        jobstask_details = {
            "job_no": result.job_no,
            "cancel_reason": cancel_reason,
            "cancel_details": result.cancel_details
        }

        logger.info(f"Successfully got cancelled jobstask details for job_no {job_no}")
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "JobsTask details retrieved successfully",
                "success": True,
                "result": jobstask_details
            },
            status_code=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(f"Error getting cancelled jobstask details for job_no {job_no}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to get cancelled jobstask details: {str(e)}",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        
        

async def get_completed_jobstask_details(
    job_no: int,
    download_all: bool,
    current_user: dict,
    db: Session
) -> Union[JSONResponse, FileResponse]:
    try:
        current_rsrc_no = get_context('rsrc_no')
        logger.info(f"Getting completed jobstask details for job_no {job_no} for user {current_rsrc_no}")

        result = (
            db.query(
                Jobs.job_no,
                Cases.case_no,
                Cases.case_number,
                Cases.case_short_name
            )
            .join(Cases, Cases.case_no == Jobs.case_no)
            .join(JobsTasks, JobsTasks.job_no == Jobs.job_no)
            .filter(
                Jobs.job_no == job_no,
                Jobs.is_archived == False,
                Cases.is_archived == False,
                JobsTasks.rsrc_no == current_rsrc_no,
                JobsTasks.is_archived == False,
                Jobs.computed_status == JobStatusEnum.COMPLETED.value
            )
            .first()
        )

        if not result:
            logger.error(f"Job with job_no {job_no} not found, not completed, or access denied")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Job with job_no {job_no} not found, not completed, or access denied",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Handle download all videos
        if download_all:
            witnesses = get_witnesses_with_videos(result.job_no, db, witness_id=None)
            video_paths = [
                video.file_path
                for witness in witnesses
                for video in witness.witness_vid
                if video.file_path and Path(video.file_path).exists()
            ]

            if not video_paths:
                return JSONResponse(
                    content={
                        "status_code": status.HTTP_404_NOT_FOUND,
                        "message": "No video files found for this job",
                        "success": False,
                        "result": {}
                    },
                    status_code=status.HTTP_404_NOT_FOUND
                )

            merged_file_path = merge_videos_ffmpeg(video_paths, result.job_no)
            return FileResponse(
                path=str(merged_file_path),
                filename=merged_file_path.name,
                media_type='video/mp4',
                headers={
                    "Content-Disposition": f"attachment; filename={merged_file_path.name}"
                }
            )

        # Fetch witnesses and attorneys
        witnesses = get_witnesses_with_videos(result.job_no, db, witness_id=None)
        attorneys = (
            db.query(Attorneys)
            .filter(
                Attorneys.job_no == result.job_no,
                Attorneys.is_archived == False
            )
            .all()
        )

        witnesses_data = [
            WitnessSchema.model_validate(witness).model_dump(mode='json')
            for witness in witnesses
        ]
        attorneys_data = [
            AttorneySchema.model_validate(attorney).model_dump(mode='json')
            for attorney in attorneys
        ]

        jobstask_details = {
            "job_no": result.job_no,
            "case_number": result.case_number,
            "case_short_name": result.case_short_name,
            "witnesses": witnesses_data,
            "attorneys": attorneys_data
        }

        logger.info(
            f"Found {len(witnesses_data)} witness(es) with videos and {len(attorneys_data)} attorney(s) "
            f"for job_no {job_no}"
        )

        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "JobsTask details retrieved successfully",
                "success": True,
                "result": jobstask_details
            },
            status_code=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(f"Error getting completed jobstask details for job_no {job_no}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to get jobstask details: {str(e)}",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


async def get_mark_as_done_status(
    job_no: int,
    case_no: int,
    current_user: dict,
    db: Session
) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')

        jobstask = (
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
                
        if not jobstask:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "JobsTask not found",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_200_OK
            )
        
        mark_as_done_status = MarkJobsTaskAsDoneSchema.model_validate(jobstask).model_dump()
        logger.info(f"Mark as done status: {mark_as_done_status}")
        
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "JobsTask fetched successfully",
                "success": True,
                "result": mark_as_done_status   
            },
            status_code=status.HTTP_200_OK
        ) 
    except Exception as e:
        logger.error(f"Error getting mark as done status: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Failed to get mark as done status",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def get_witnesses_with_videos(job_no: int, db: Session, witness_id: Optional[int] = None) -> List[Witnesses]:
    query = (
        db.query(Witnesses)
        .options(
            joinedload(Witnesses.witness_vid),
            with_loader_criteria(
                WitnessVideos, 
                WitnessVideos.is_archived == False, 
                include_aliases=True
            ),
        )
        .filter(
            Witnesses.job_no == job_no,
            Witnesses.is_archived == False
        )
    )
    
    if witness_id is not None:
        query = query.filter(Witnesses.id == witness_id)
    
    return query.all()


def merge_videos_ffmpeg(video_paths: List[str], job_no: int) -> Path:
    if not video_paths:
        raise ValueError("No video paths provided")
    
    ffmpeg = None
    
    for path in ['/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg', '/bin/ffmpeg', '/opt/bin/ffmpeg']:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            ffmpeg = path
            logger.info(f"Found ffmpeg at: {ffmpeg}")
            break
    
    if not ffmpeg:
        try:
            result = subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True, check=False, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                ffmpeg = result.stdout.strip()
                logger.info(f"Found ffmpeg via which: {ffmpeg}")
        except Exception:
            pass
    
    if not ffmpeg:
        logger.error("FFmpeg not found in any location")
        raise HTTPException(
            status_code=500, 
            detail="FFmpeg not found. Install it: sudo apt install ffmpeg -y"
        )
    
    temp_dir = Path(tempfile.gettempdir())
    date_str = datetime.now().strftime('%Y-%m-%d')
    merged_file_path = temp_dir / f"jobstask_{job_no}_all_videos_{date_str}.mp4"
    concat_file = temp_dir / f"concat_list_{job_no}_{date_str}.txt"
    
    try:
        project_root = Path(__file__).resolve().parent.parent.parent
        
        with open(concat_file, 'w') as f:
            for video_path in video_paths:
                abs_path = (project_root / video_path).resolve() if not os.path.isabs(video_path) else Path(video_path).resolve()
                if abs_path.exists():
                    f.write(f"file '{str(abs_path).replace(chr(39), chr(39)+chr(92)+chr(92)+chr(39)+chr(39))}'\n")
        
        result = subprocess.run(
            [ffmpeg, '-f', 'concat', '-safe', '0', '-i', str(concat_file), '-c', 'copy', '-y', str(merged_file_path)], 
            capture_output=True, text=True, check=True, timeout=300
        )
        logger.info(f"Merged videos for job_no {job_no}")
        return merged_file_path
        
    except subprocess.CalledProcessError as e:
        logger.warning(f"FFmpeg copy failed, retrying with re-encoding: {e.stderr}")
        try:
            subprocess.run(
                [ffmpeg, '-f', 'concat', '-safe', '0', '-i', str(concat_file), '-c:v', 'libx264', '-c:a', 'aac', '-y', str(merged_file_path)], 
                capture_output=True, text=True, check=True, timeout=600
            )
            logger.info(f"Merged videos with re-encoding for job_no {job_no}")
            return merged_file_path
        except subprocess.CalledProcessError as e2:
            logger.error(f"FFmpeg re-encoding failed: {e2.stderr}")
            raise HTTPException(status_code=500, detail=f"Video merge failed: {e2.stderr}")
    finally:
        if concat_file.exists():
            concat_file.unlink()


async def list_jobstasks_by_case(
    current_user: dict,
    db: Session,
) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')
        logger.info(f"Fetching jobstasks for user {current_rsrc_no}")
        
        # Get resource and its job_no for current user
        resource_job = db.query(JobsTasks.job_no).filter(
            JobsTasks.rsrc_no == current_rsrc_no
        ).first()
        
        if not resource_job:
            logger.warning(f"No resource found for user {current_rsrc_no} or resource has no job tasks")
            return [JobsTaskListSchema.model_validate(jobstask).model_dump() for jobstask in []]
        
        job_no = resource_job[0]
        
        # Find the Job using job_no
        job = db.query(Jobs).filter(Jobs.job_no == job_no).first()
        
        if not job:
            logger.warning(f"No job found for job_no {job_no}")
            return [JobsTaskListSchema.model_validate(jobstask).model_dump() for jobstask in []]
        
        # Filter jobstasks by case (from the job's case_no)
        jobstasks = (
            db.query(JobsTasks)
            .join(Jobs, JobsTasks.job_no == Jobs.job_no)
            .join(Cases, Jobs.case_no == Cases.case_no)
            .options(joinedload(JobsTasks.job).joinedload(Jobs.case))
            .filter(
                Cases.case_no == job.case_no,
                JobsTasks.rsrc_no == current_rsrc_no
            )
            .all()
        )
        
        logger.info(f"Found {len(jobstasks)} jobstasks for case_no {job.case_no}")
        return [JobsTaskListSchema.model_validate(jobstask).model_dump() for jobstask in jobstasks]

    except Exception as e:
        logger.error(f"Error fetching jobstasks by case: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Unable to fetch jobstasks for requested case',
        )

async def list_pending_jobstasks(
    page: Optional[int],
    page_size: Optional[int],
    current_user: dict,
    db: Session
) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')
        today = datetime.combine(datetime.now().date(), datetime.min.time())

        # Get all job_nos assigned to current resource
        job_nos = [
            row.job_no for row in db.query(JobsTasks.job_no).filter(
                JobsTasks.rsrc_no == current_rsrc_no,
                JobsTasks.job_no.isnot(None)
            ).all()
        ]

        if not job_nos:
            logger.info(f"No job_nos found for resource {current_rsrc_no}")
            empty_response = {
                "status_code": status.HTTP_200_OK,
                "message": "Pending jobstasks retrieved successfully",
                "success": True,
                "result": []
            }
            if page is not None and page_size is not None:
                empty_response["pagination"] = {
                    "page": page,
                    "page_size": page_size,
                    "total": 0,
                    "total_pages": 0,
                    "has_next": False,
                    "has_previous": False
                }
            return JSONResponse(content=empty_response, status_code=status.HTTP_200_OK)

        # Base query
        base_query = (
            db.query(Jobs)
            .join(Cases, Jobs.case_no == Cases.case_no)
            .filter(
                Jobs.job_no.in_(job_nos),
                Jobs.is_archived == False,
                Cases.is_archived == False,
                Jobs.job_date <= today,
                Jobs.session_completed == False,
                Jobs.computed_status != JobStatusEnum.CANCELLED.value
            )
        )

        def attach_video_status(jobstasks_data: list) -> list:
            jnos = [j["job_no"] for j in jobstasks_data]
            status_by_job = get_video_upload_status(jnos, db)
            for job_data in jobstasks_data:
                job_status = status_by_job.get(job_data["job_no"], {"witness_videos_status": {}})
                job_data["witness_videos_status"] = job_status.get("witness_videos_status", {})
            return jobstasks_data

        # No pagination
        if page is None or page_size is None:
            jobstasks = base_query.order_by(Jobs.job_date.asc()).all()
            jobstasks_data = attach_video_status(
                [JobsTaskListSchema.model_validate(j).model_dump(mode='json') for j in jobstasks]
            )
            logger.info(f"Found {len(jobstasks_data)} pending jobstasks for user {current_rsrc_no}")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Pending jobstasks retrieved successfully",
                    "success": True,
                    "result": jobstasks_data
                },
                status_code=status.HTTP_200_OK
            )

        # With pagination
        total = base_query.count()
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        jobstasks = (
            base_query
            .order_by(Jobs.job_date.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        jobstasks_data = attach_video_status(
            [JobsTaskListSchema.model_validate(j).model_dump(mode='json') for j in jobstasks]
        )
        logger.info(f"Found {len(jobstasks_data)} pending jobstasks (page {page}/{total_pages}) for user {current_rsrc_no}")
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Pending jobstasks retrieved successfully",
                "success": True,
                "result": jobstasks_data,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_previous": page > 1
                }
            },
            status_code=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(f"Error fetching pending jobstasks: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Unable to fetch pending jobstasks",
                "success": False,
                "result": [],
                "pagination": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        

async def list_upcoming_jobstasks(
    page: Optional[int],
    page_size: Optional[int],
    current_user: dict,
    db: Session
) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')
        tomorrow = datetime.combine(
            datetime.now().date() + timedelta(days=1),
            datetime.min.time()
        )

        # Get all job_nos assigned to current resource
        job_nos = [
            row.job_no for row in db.query(JobsTasks.job_no).filter(
                JobsTasks.rsrc_no == current_rsrc_no,
                JobsTasks.job_no.isnot(None)
            ).all()
        ]

        if not job_nos:
            logger.info(f"No job_nos found for resource {current_rsrc_no}")
            empty_response = {
                "status_code": status.HTTP_200_OK,
                "message": "Upcoming jobstasks retrieved successfully",
                "success": True,
                "result": []
            }
            if page is not None and page_size is not None:
                empty_response["pagination"] = {
                    "page": page,
                    "page_size": page_size,
                    "total": 0,
                    "total_pages": 0,
                    "has_next": False,
                    "has_previous": False
                }
            return JSONResponse(content=empty_response, status_code=status.HTTP_200_OK)

        # Base query
        base_query = (
            db.query(Jobs)
            .join(Cases, Jobs.case_no == Cases.case_no)
            .filter(
                Jobs.job_no.in_(job_nos),
                Jobs.is_archived == False,
                Cases.is_archived == False,
                Jobs.job_date >= tomorrow,
                Jobs.session_completed == False,
                Jobs.computed_status != JobStatusEnum.CANCELLED.value,
            )
        )

        # No pagination
        if page is None or page_size is None:
            jobstasks = base_query.order_by(Jobs.job_date.asc(), Jobs.start_time.asc()).all()
            jobstasks_data = [JobsTaskListSchema.model_validate(j).model_dump(mode='json') for j in jobstasks]
            logger.info(f"Found {len(jobstasks_data)} upcoming jobstasks for user {current_rsrc_no}")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Upcoming jobstasks retrieved successfully",
                    "success": True,
                    "result": jobstasks_data
                },
                status_code=status.HTTP_200_OK
            )

        # With pagination
        total = base_query.count()
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        jobstasks = (
            base_query
            .order_by(Jobs.job_date.asc(), Jobs.start_time.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        jobstasks_data = [JobsTaskListSchema.model_validate(j).model_dump(mode='json') for j in jobstasks]
        logger.info(f"Found {len(jobstasks_data)} upcoming jobstasks (page {page}/{total_pages}) for user {current_rsrc_no}")
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Upcoming jobstasks retrieved successfully",
                "success": True,
                "result": jobstasks_data,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_previous": page > 1
                }
            },
            status_code=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(f"Error fetching upcoming jobstasks: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Unable to fetch upcoming jobstasks",
                "success": False,
                "result": [],
                "pagination": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


async def get_session_start_time(
    job_no: int,
    current_user: dict,
    db: Session
) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')

        job = (
            db.query(
                Jobs.computed_status,
                Jobs.actual_session_start_time
            )
            .join(Cases, Cases.case_no == Jobs.case_no)
            .join(JobsTasks, JobsTasks.job_no == Jobs.job_no)
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

        status_map = {
            JobStatusEnum.SESSION_IN_PROGRESS.value: {
                "message": "Session is in progress",
                "result": job.actual_session_start_time.isoformat()
                    if job.actual_session_start_time else {}
            },
            JobStatusEnum.SESSION_NOT_STARTED.value: {
                "message": "Session is not started",
                "result": {}
            },
            JobStatusEnum.COMPLETED.value: {
                "message": "Session is completed",
                "result": {}
            },
            JobStatusEnum.SCHEDULED.value: {
                "message": "Session is scheduled",
                "result": {}
            },
        }

        computed_status = job.computed_status
        status_info = status_map.get(computed_status, {
            "message": "Unknown session status",
            "result": {}
        })

        logger.info(f"Session status: {computed_status} for job_no {job_no}")

        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": status_info["message"],
                "success": True,
                "status": computed_status,
                "result": status_info["result"]
            },
            status_code=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(f"Error getting session start time: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Unable to get session start time",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


async def start_session(
    job_no: int,
    current_user: dict,
    db: Session
) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')
        now = get_timezone_now()

        job = (
            db.query(Jobs)
            .join(JobsTasks, JobsTasks.job_no == Jobs.job_no)
            .join(Cases, Cases.case_no == Jobs.case_no)
            .filter(
                Jobs.job_no == job_no,
                Jobs.is_archived == False,
                Cases.is_archived == False,
                JobsTasks.rsrc_no == current_rsrc_no,
                JobsTasks.is_archived == False,
                Jobs.session_completed == False
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

        update_payload = {
            "actual_session_start_time": now,
            "computed_status": JobStatusEnum.SESSION_IN_PROGRESS.value,
            "last_modified_at": now,
            "last_modified_by": current_rsrc_no
        }
        for key, value in update_payload.items():
            setattr(job, key, value)

        db.add(job)
        db.commit()

        logger.info(f"Session started for job_no {job_no} at {job.actual_session_start_time}")

        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Session started successfully",
                "success": True,
                "result": {
                    "job_no": job.job_no,
                    "start_time": job.actual_session_start_time.isoformat() if job.actual_session_start_time else None,
                    "computed_status": job.computed_status
                }
            },
            status_code=status.HTTP_200_OK
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error starting session for job_no {job_no}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Failed to start session",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


async def end_session(
    job_no: int,
    current_user: dict,
    db: Session
) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')
        now = get_timezone_now()

        job = (
            db.query(Jobs)
            .join(JobsTasks, JobsTasks.job_no == Jobs.job_no)
            .join(Cases, Cases.case_no == Jobs.case_no)
            .filter(
                Jobs.job_no == job_no,
                Jobs.is_archived == False,
                Cases.is_archived == False,
                JobsTasks.rsrc_no == current_rsrc_no,
                JobsTasks.is_archived == False,
                Jobs.computed_status == JobStatusEnum.SESSION_IN_PROGRESS.value,
                Jobs.actual_session_start_time.isnot(None),
                Jobs.session_completed == False
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

        # Calculate session duration
        duration = now - job.actual_session_start_time
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        session_duration = f"{hours}:{minutes:02d}:{seconds:02d}"

        # Update via setattr
        update_payload = {
            "actual_session_end_time": now,
            "session_duration": session_duration,
            "session_completed": True,
            "computed_status": JobStatusEnum.COMPLETED.value,
            "last_modified_at": now,
            "last_modified_by": current_rsrc_no
        }
        for key, value in update_payload.items():
            setattr(job, key, value)

        db.add(job)
        db.commit()

        logger.info(f"Session ended for job_no {job_no}. Duration: {job.session_duration}")

        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Session ended successfully",
                "success": True,
                "result": {
                    "job_no": job.job_no,
                    "start_time": job.actual_session_start_time.isoformat() if job.actual_session_start_time else None,
                    "end_time": job.actual_session_end_time.isoformat() if job.actual_session_end_time else None,
                    "duration": job.session_duration,
                    "computed_status": job.computed_status
                }
            },
            status_code=status.HTTP_200_OK
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error ending session for job_no {job_no}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Failed to end session",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


async def cancel_jobstask(
    job_no: int,
    payload: JobsTaskCancelSchema,
    current_user: dict,
    db: Session
) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')
        now = get_timezone_now()

        job = (
            db.query(Jobs)
            .join(Cases, Jobs.case_no == Cases.case_no)
            .join(JobsTasks, JobsTasks.job_no == Jobs.job_no)
            .filter(
                Jobs.job_no == job_no,
                Jobs.is_archived == False,
                Cases.is_archived == False,
                JobsTasks.is_archived == False,
                JobsTasks.rsrc_no == current_rsrc_no
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

        logger.info(f"Cancelling job {job_no} with reason: {payload.cancel_reason}")

        cancel_payload = {
            "cancel_reason": payload.cancel_reason or None,
            "cancel_details": payload.cancel_details,
            "cancel_by": current_rsrc_no,
            "cancel_date": now,
            "computed_status": JobStatusEnum.CANCELLED.value,
            "last_modified_at": now,
            "last_modified_by": current_rsrc_no
        }
        for key, value in cancel_payload.items():
            setattr(job, key, value)

        db.add(job)
        db.commit()

        logger.info(f"Job {job_no} cancelled successfully with reason: {job.cancel_reason}")
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Job cancelled successfully",
                "success": True,
                "result": {}
            },
            status_code=status.HTTP_200_OK
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error cancelling job {job_no}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Failed to cancel job",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


async def cancelled_and_completed_jobstasks(
    type: str,
    start_date: Optional[date],
    end_date: Optional[date],
    page: int,
    page_size: int,
    current_user: dict,
    db: Session,
    job_no: Optional[Union[int, str]] = None,
    witness_name: Optional[str] = None,
    case_name: Optional[str] = None,
    case_number: Optional[str] = None
) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')
        if type not in ['Cancelled', 'Completed']:
            logger.error(f"Invalid type: {type}")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "Invalid type. Must be 'Cancelled' or 'Completed'",
                    "success": False,
                    "result": [],
                    "pagination": {}
                },
                status_code=status.HTTP_400_BAD_REQUEST
            )

        logger.info(
            f"Listing {type} jobstasks for rsrc {current_rsrc_no} ,job_no={job_no}"
        )

        # Base query
        query = (
            db.query(Jobs)
            .join(JobsTasks, JobsTasks.job_no == Jobs.job_no)
            .join(Cases, Jobs.case_no == Cases.case_no)
            .options(joinedload(Jobs.case))
            .filter(
                Cases.is_archived == False,
                Jobs.is_archived == False,
                JobsTasks.is_archived == False,
                JobsTasks.rsrc_no == current_rsrc_no
            )
        )

        # Status filter
        if type == 'Cancelled':
            query = query.filter(
                Jobs.computed_status == JobStatusEnum.CANCELLED.value
            )
        else:
            query = query.filter(
                Jobs.computed_status == JobStatusEnum.COMPLETED.value,
                Jobs.session_completed == True
            )

        # Date filters
        if start_date:
            query = query.filter(func.date(Jobs.job_date) >= start_date)
        if end_date:
            query = query.filter(func.date(Jobs.job_date) <= end_date)

        # Search filters
        if job_no is not None:
            job_no_str = str(job_no).strip()
            if job_no_str:
                query = query.filter(
                    JobsTasks.job_no.cast(String).ilike(f'%{job_no_str}%')
                )

        if case_name:
            case_name_str = str(case_name).strip()
            if case_name_str:
                query = query.filter(
                    Cases.case_short_name.ilike(f'%{case_name_str}%')
                )

        if case_number is not None:
            case_number_str = str(case_number).strip()
            if case_number_str:
                query = query.filter(
                    Cases.case_number.cast(String).ilike(f'%{case_number_str}%')
                )

        if witness_name:
            witness_name_str = str(witness_name).strip()
            if witness_name_str:
                query = (
                    query
                    .join(Witnesses, Witnesses.job_no == Jobs.job_no)
                    .filter(Witnesses.witness_name.ilike(f'%{witness_name_str}%'))
                    .distinct()
                )

        # Pagination
        total = query.with_entities(func.count(JobsTasks.task_no)).scalar()
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        jobstasks = (
            query
            .order_by(Jobs.job_date.desc(), JobsTasks.task_no.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        jobstasks_data = [
            JobsTaskCancelledAndCompletedSchema.model_validate(jobstask).model_dump(mode='json')
            for jobstask in jobstasks
        ]

        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": f"{type} jobstasks listed successfully" if jobstasks_data else f"No {type} jobstasks found",
                "success": True,
                "result": jobstasks_data,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_previous": page > 1
                }
            },
            status_code=status.HTTP_200_OK
        )

    except ValueError as e:
        logger.error(f"Invalid parameter value: {str(e)}")
        return JSONResponse(
            content={
                "status_code": status.HTTP_400_BAD_REQUEST,
                "message": f"Invalid parameter: {str(e)}",
                "success": False,
                "result": []
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error listing {type} jobstasks: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to list {type} jobstasks",
                "success": False,
                "result": []
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        

async def mark_jobstask_as_done(
    job_no: int,
    type: str,
    body: dict,
    current_user: dict,
    db: Session
) -> JSONResponse:
    try:
        now = get_timezone_now()
        current_rsrc_no = get_context('rsrc_no')
        logger.info(f" type: {type}")
        valid_types = ['case', 'witnesses', 'attorneys', 'billings', 'equipment_time']
        if type not in valid_types:
            logger.error(f"Invalid type: {type}")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": f"Invalid type. Must be one of: {', '.join(valid_types)}",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_400_BAD_REQUEST
            )

        is_done = body.get("is_done", False)

        job = (
            db.query(Jobs)
            .join(JobsTasks, JobsTasks.job_no == Jobs.job_no)
            .filter(
                Jobs.job_no == job_no,
                Jobs.is_archived == False,
                JobsTasks.is_archived == False,
                JobsTasks.rsrc_no == current_rsrc_no
            )
            .first()
        )

        if not job:
            logger.warning(f'Job {job_no} not found for user {current_rsrc_no}')
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Job not found or access denied",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Update mark_is_done field on Jobs
        setattr(job, f"mark_is_done_{type}", is_done)
        job.last_modified_at = now
        job.last_modified_by = current_rsrc_no
        db.add(job)
        db.commit()

        logger.info(f'Job {job_no} marked as done: {type} = {is_done}')
        message = f"Job {job_no} {type} marked as {'done' if is_done else 'not done'} successfully"

        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": message,
                "success": True,
                "result": {
                    "job_no": job.job_no,
                    "type": type,
                    "mark_is_done": is_done
                }
            },
            status_code=status.HTTP_200_OK
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error marking job {job_no} as done: {type}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to mark job {job_no} as done: {type}",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error marking jobstask {job_no} as done: {type}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to mark jobstask {job_no} as done: {type}",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def _get_calendar_events_query(
    db: Session,
    current_rsrc_no: int,
    start_date: date,
    end_date: date
) -> List[Jobs]:
    return (
        db.query(Jobs)
        .join(JobsTasks, JobsTasks.job_no == Jobs.job_no)
        .join(Cases, Jobs.case_no == Cases.case_no)
        .options(joinedload(Jobs.case))
        .filter(
            Jobs.is_archived == False,
            JobsTasks.rsrc_no == current_rsrc_no,
            JobsTasks.is_archived == False,
            Cases.is_archived == False,
            Jobs.job_date >= start_date,
            Jobs.job_date <= end_date
        )
        .order_by(Jobs.job_date, Jobs.start_time)
        .all()
    )


async def get_calendar_events(
    year: Optional[int],
    month: Optional[int],
    day: Optional[int],
    start_date: Optional[date],
    end_date: Optional[date],
    current_user: dict,
    db: Session
) -> JSONResponse:
    try:
        current_rsrc_no = get_context('rsrc_no')
        start_date_filter: date
        end_date_filter: date
        filter_type: str = ""
        
        if year is not None and month is not None and day is not None:
            if not (1 <= month <= 12):
                logger.error(f"Invalid month: {month}")
                return JSONResponse(
                    content={
                        "status_code": status.HTTP_400_BAD_REQUEST,
                        "message": "Invalid month. Must be between 1 and 12",
                        "success": False,
                        "result": []
                    },
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            if not (1 <= day <= 31):
                logger.error(f"Invalid day: {day}")
                return JSONResponse(
                    content={
                        "status_code": status.HTTP_400_BAD_REQUEST,
                        "message": "Invalid day. Must be between 1 and 31",
                        "success": False,
                        "result": []
                    },
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                target_date = date(year, month, day)
            except ValueError as e:
                logger.error(f"Invalid date: {str(e)}")
                return JSONResponse(
                    content={
                        "status_code": status.HTTP_400_BAD_REQUEST,
                        "message": f"Invalid date: {str(e)}",
                        "success": False,
                        "result": []
                    },
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            start_date_filter, end_date_filter = get_date_range_for_week(year, month, day)
            filter_type = f"week containing {target_date}"
            logger.info(f"Fetching calendar events for {filter_type} for user {current_rsrc_no}")
            
        elif year is not None and month is not None:
            if not (1 <= month <= 12):
                logger.error(f"Invalid month: {month}")
                return JSONResponse(
                    content={
                        "status_code": status.HTTP_400_BAD_REQUEST,
                        "message": "Invalid month. Must be between 1 and 12",
                        "success": False,
                        "result": []
                    },
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            start_date_filter, end_date_filter = get_date_range_for_month(year, month)
            filter_type = f"month {year}-{month:02d}"
            logger.info(f"Fetching calendar events for {filter_type} for user {current_rsrc_no}")
            
        elif start_date is not None and end_date is not None:
            if start_date > end_date:
                logger.error(f"start_date must be before or equal to end_date")
                return JSONResponse(
                    content={
                        "status_code": status.HTTP_400_BAD_REQUEST,
                        "message": "start_date must be before or equal to end_date",
                        "success": False,
                        "result": []
                    },
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            start_date_filter = start_date
            end_date_filter = end_date
            filter_type = f"custom range {start_date} to {end_date}"
            logger.info(f"Fetching calendar events for {filter_type} for user {current_rsrc_no}")
            
        else:
            logger.error(f"Invalid parameters")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": (
                        "Invalid parameters. Provide one of:\n"
                        "1. year + month + day (for week view)\n"
                        "2. year + month (for month view)\n"
                        "3. start_date + end_date (for custom range)"
                    ),
                    "success": False,
                    "result": []
                },
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        jobs = _get_calendar_events_query(db, current_rsrc_no, start_date_filter, end_date_filter)
        events = [jobstask_to_calendar_event(job, db).model_dump(mode='json') for job in jobs]
        logger.info(f"Found {len(events)} calendar events for {filter_type}")
        
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Calendar events retrieved successfully",
                "success": True,
                "result": events
            },
            status_code=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Error fetching calendar events: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to fetch calendar events: {str(e)}",
                "success": False,
                "result": []
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )