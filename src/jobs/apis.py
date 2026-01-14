from typing import List, Optional, Union
from datetime import datetime, timedelta, date
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, with_loader_criteria
import subprocess
import tempfile
import os
from pathlib import Path

from src.jobs.models import Jobs
from src.core.logger import logger
from src.cases.models import Cases
from src.core.context import get_context
from src.jobs.schema import (
    JobSchema, 
    CancelJobSchema, 
    CancelledAndCompletedJobSchema, 
    MarkJobAsDoneSchema
)
from src.jobs.models import JobStatusEnum, CancelReasonEnum
from src.jobs.utils import (
    job_to_calendar_event,
    get_date_range_for_month,
    get_date_range_for_week,
    get_video_upload_status
)
from src.witnesses.models import Witnesses
from src.witness_videos.models import WitnessVideos
from src.attorneys.models import Attorneys
from src.witnesses.schema import WitnessSchema
from src.attorneys.schema import AttorneySchema


async def get_cancelled_job_details(
    job_no: int,
    current_user: dict,
    db: Session
) -> JSONResponse:
    try:
        user_entered_by = get_context('entered_by')
        logger.info(f"Getting cancelled job details for job_no {job_no} for user {user_entered_by}")
        
        job = (
            db.query(Jobs)
            .join(Cases, Jobs.case_no == Cases.case_no)
            .filter(Cases.is_archived == False)
            .filter(Jobs.is_archived == False)
            .filter(Jobs.job_no == job_no)
            .filter(Cases.entered_by == user_entered_by)
            .filter(Jobs.entered_by == user_entered_by)
            .filter(Jobs.computed_status == JobStatusEnum.CANCELLED.value)
            .first()
        )

        if not job:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Job with job_no {job_no} not found, not cancelled, or access denied",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )

        if isinstance(job.cancel_reason, CancelReasonEnum):
            cancel_reason_value = job.cancel_reason.value
        else:
            cancel_reason_value = job.cancel_reason

        job_details = {
            "job_no": job.job_no,
            "cancel_reason": cancel_reason_value,
            "cancel_details": job.cancel_details,
        }
        logger.info(f"Job details: {job_details}")
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Job details retrieved successfully",
                "success": True,
                "result": job_details
            },
            status_code=status.HTTP_200_OK
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cancelled job details for job_no {job_no}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to get cancelled job details: {str(e)}",    
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


async def get_completed_job_details(
    job_no: int,
    download_all: bool,
    current_user: dict,
    db: Session
) -> Union[JSONResponse, FileResponse]:
    try:
        user_entered_by = get_context('entered_by')
        logger.info(f"Getting completed job details for job_no {job_no} for user {user_entered_by}")
        
        job = (
            db.query(Jobs)
            .join(Cases, Jobs.case_no == Cases.case_no)
            .filter(Cases.is_archived == False)
            .filter(Jobs.is_archived == False)
            .filter(Jobs.job_no == job_no)
            .filter(Cases.entered_by == user_entered_by)
            .filter(Jobs.entered_by == user_entered_by)
            .filter(
                (Jobs.computed_status == JobStatusEnum.COMPLETED.value)
            )
            .first()
        )
        logger.info(f"Job=--------------------------: {user_entered_by}")
        if not job:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Job with job_no {job_no} not found, not completed, or access denied",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )

        witnesses = get_witnesses_with_videos(job_no, db, witness_id=None)
        
        attorneys = (
            db.query(Attorneys)
            .filter(
                Attorneys.job_no == job_no,
                Attorneys.is_archived == False
            )
            .all()
        )
        
        if download_all:
            video_paths = []
            for witness in witnesses:
                for video in witness.witness_vid:
                    if video.file_path and Path(video.file_path).exists():
                        video_paths.append(video.file_path)
            
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
            
            merged_file_path = merge_videos_ffmpeg(video_paths, job_no)
            merged_filename = merged_file_path.name
            
            return FileResponse(
                path=str(merged_file_path),
                filename=merged_filename,
                media_type='video/mp4',
                headers={
                    "Content-Disposition": f"attachment; filename={merged_filename}"
                }
            )
        
        witnesses_data = [
            WitnessSchema.model_validate(witness).model_dump(mode='json') 
            for witness in witnesses
        ]
        
        attorneys_data = [
            AttorneySchema.model_validate(attorney).model_dump(mode='json')
            for attorney in attorneys
        ]
        
        job_details = {
            "job_no": job.job_no,
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
                "message": "Job details retrieved successfully",
                "success": True,
                "result": job_details
            },
            status_code=status.HTTP_200_OK
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting completed job details for job_no {job_no}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to get job details: {str(e)}",
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
        logger.info(f"Getting mark as done status for job_no {job_no} and case_no {case_no}")
        job = (
            db.query(Jobs)
            .join(Cases, Jobs.case_no == Cases.case_no)
            .filter(Jobs.job_no == job_no, Jobs.is_archived == False)
            .options(joinedload(Jobs.case))
            .first()
        )
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
        logger.info(f"Job: {job}")
        mark_as_done_status = MarkJobAsDoneSchema.model_validate(job).model_dump()
        logger.info(f"Mark as done status: {mark_as_done_status}")
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Job fetched successfully",
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
    
    temp_dir = Path(tempfile.gettempdir())
    merged_filename = f"job_{job_no}_all_videos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    merged_file_path = temp_dir / merged_filename
    
    concat_file = temp_dir / f"concat_list_{job_no}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    try:
        project_root = Path(__file__).resolve().parent.parent.parent
        
        valid_video_count = 0
        with open(concat_file, 'w') as f:
            for video_path in video_paths:
                if not os.path.isabs(video_path):
                    abs_video_path = (project_root / video_path).resolve()
                else:
                    abs_video_path = Path(video_path).resolve()
                
                if not abs_video_path.exists():
                    logger.warning(f"Video file not found: {abs_video_path} (original: {video_path})")
                    continue
                
                
                escaped_path = str(abs_video_path).replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")
                valid_video_count += 1
        
        if valid_video_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No valid video files found to merge"
            )
        
        ffmpeg_cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(concat_file),
            '-c', 'copy',
            '-y',
            str(merged_file_path)
        ]
        
        subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        logger.info(f"Successfully merged {valid_video_count} videos for job_no {job_no}")
        return merged_file_path
        
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error merging videos: {e.stderr}", exc_info=True)
        try:
            logger.info("Retrying with re-encoding...")
            ffmpeg_cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_file),
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-y',
                str(merged_file_path)
            ]
            subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=True)
            logger.info(f"Successfully merged videos with re-encoding for job_no {job_no}")
            return merged_file_path
        except subprocess.CalledProcessError as e2:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to merge videos: {e2.stderr}. Please ensure FFmpeg is installed."
            )
    finally:
        if concat_file.exists():
            concat_file.unlink()

async def list_jobs(
    current_user: dict,
) -> JSONResponse:
    return Jobs.fetch_records({"entered_by": current_user.get("id")})


async def list_jobs_by_case(
    current_user: dict,
    db: Session,
) -> JSONResponse:
    try:
        user_entered_by = get_context('entered_by')
        logger.info(f"Fetching jobs for user {user_entered_by}")
        jobs = (
            db.query(Jobs)
            .join(Cases, Jobs.case_no == Cases.case_no)
            .options(joinedload(Jobs.case))
            .filter(Cases.entered_by == user_entered_by)
            .all()
        )
        return [JobSchema.model_validate(job).model_dump() for job in jobs]

    except Exception as e:
        logger.error(f"Error fetching jobs by case: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Unable to fetch jobs for the requested case',
        )

async def list_pending_jobs(
    page: int,
    page_size: int,
    current_user: dict,
    db: Session
) -> JSONResponse:
    try:
        user_entered_by = get_context('entered_by')
        today = datetime.now().date()
        
        query = (
            db.query(Jobs)
            .join(Cases, Jobs.case_no == Cases.case_no)
            .options(joinedload(Jobs.case))
            .filter(Cases.is_archived == False)
            .filter(Jobs.is_archived == False)
            .filter(Cases.entered_by == user_entered_by)
            .filter(Jobs.entered_by == user_entered_by)
            .filter(Jobs.job_date <= datetime.combine(today, datetime.min.time()))
            .filter(Jobs.session_completed == False)
            .filter(Jobs.computed_status != JobStatusEnum.CANCELLED.value)
        )
        
        total = query.count()
        
        jobs = (
            query
            .order_by(Jobs.job_date.asc(), Jobs.start_time.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        jobs_data = [JobSchema.model_validate(job).model_dump(mode='json') for job in jobs]
        job_nos = [job["job_no"] for job in jobs_data]
        status_by_job = get_video_upload_status(job_nos, db)
        
        for job_data in jobs_data:
            job_status = status_by_job.get(job_data["job_no"], {"witness_videos_status": {}})
            job_data["witness_videos_status"] = job_status.get("witness_videos_status", {})

        logger.info(f"Found {len(jobs_data)} pending jobs (page {page}/{total_pages}) for user {user_entered_by}")
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Pending jobs retrieved successfully",
                "success": True,
                "result": jobs_data,
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
        logger.error(f"Error fetching pending jobs: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Unable to fetch pending jobs",
                "success": False,
                "result": [],
                "pagination": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

async def list_upcoming_jobs(
    page: int,
    page_size: int,
    current_user: dict,
    db: Session
) -> JSONResponse:
    try:
        user_entered_by = get_context('entered_by')
        tomorrow = (datetime.now().date() + timedelta(days=1))
        logger.info(f"page_size: {page_size}")
        query = (
            db.query(Jobs)
            .join(Cases, Jobs.case_no == Cases.case_no)
            .options(joinedload(Jobs.case))
            .filter(Cases.is_archived == False)
            .filter(Jobs.is_archived == False)
            .filter(Cases.entered_by == user_entered_by)
            .filter(Jobs.session_completed == False)
            .filter(Jobs.job_date >= datetime.combine(tomorrow, datetime.min.time()))
            .filter(Jobs.entered_by == user_entered_by)
            .filter(Jobs.computed_status != JobStatusEnum.CANCELLED.value)
        )
        
        total = query.count()
        
        jobs = (
            query
            .order_by(Jobs.job_date.asc(), Jobs.start_time.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        
        jobs_data = [JobSchema.model_validate(job).model_dump(mode='json') for job in jobs]
        
        logger.info(f"Found {len(jobs_data)} upcoming jobs (page {page}/{total_pages}) for user {user_entered_by}")
        
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Upcoming jobs retrieved successfully",
                "success": True,
                "result": jobs_data,
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
        logger.error(f"Error fetching upcoming jobs: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Unable to fetch upcoming jobs",
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
        logger.info(f"Getting session start time for job_no {job_no}")
        user_entered_by = get_context('entered_by')
        job = (
            db.query(Jobs)
            .join(Cases, Jobs.case_no == Cases.case_no)
            .filter(Cases.is_archived == False)
            .filter(Jobs.job_no == job_no)
            .filter(Jobs.is_archived == False)
            .filter(Cases.entered_by == user_entered_by)
            .first()
        )
        if not job:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Job with job_no {job_no} not found or access denied",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )
        session_start_time_is_on = True if job.actual_session_start_time else False
        if job.computed_status == JobStatusEnum.SESSION_IN_PROGRESS.value:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Session is in progress",
                    "success": True,
                    "status": job.computed_status,
                    "result": job.actual_session_start_time.isoformat() if session_start_time_is_on else {}
                },
                status_code=status.HTTP_200_OK
            )
        if job.computed_status == JobStatusEnum.SESSION_NOT_STARTED.value:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Session is not started",
                    "success": True,
                    "status": job.computed_status,
                    "result": {}
                },  
                status_code=status.HTTP_200_OK
            )
        if job.computed_status == JobStatusEnum.COMPLETED.value:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Session is completed",
                    "success": True,
                    "status": job.computed_status,
                    "result": {}
                },
                status_code=status.HTTP_200_OK
            )
        if job.computed_status == JobStatusEnum.SCHEDULED.value:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Session is scheduled",
                    "success": True,
                    "status": job.computed_status,
                    "result": {}
                },
                status_code=status.HTTP_200_OK
            )


    except Exception as e:
        logger.error(f"Error getting session for job_no {job_no}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Failed to get session",
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
        user_entered_by = get_context('entered_by')
        
        job = (
            db.query(Jobs)
            .join(Cases, Jobs.case_no == Cases.case_no)
            .filter(Jobs.job_no == job_no)
            .filter(Cases.entered_by == user_entered_by)
            .filter(Jobs.session_completed == False)
            .first()
        )
        
        if not job:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Job with job_no {job_no} not found or access denied",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )
    
        
        job.actual_session_start_time = datetime.now()
        job.computed_status =  JobStatusEnum.SESSION_IN_PROGRESS.value
        
        db.commit()
        db.refresh(job)
        
        logger.info(f"Session started for job_no {job_no} at {job.actual_session_start_time}")
        
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Session started successfully",
                "success": True,
                "result": {
                    "job_no": job.job_no,
                    "start_time": job.actual_session_start_time.isoformat(),
                    "computed_status": job.computed_status
                }
            },
            status_code=status.HTTP_200_OK
        )
        
    except HTTPException:
        raise
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
        user_entered_by = get_context('entered_by')
        
        job = (
            db.query(Jobs)
            .join(Cases, Jobs.case_no == Cases.case_no)
            .filter(Cases.is_archived == False)
            .filter(Jobs.is_archived == False)
            .filter(Jobs.job_no == job_no)
            .filter(Jobs.computed_status == JobStatusEnum.SESSION_IN_PROGRESS.value)
            .filter(Jobs.actual_session_start_time is not None)
            .filter(Cases.entered_by == user_entered_by)
            .filter(Jobs.session_completed == False)
            .first()
        )
        
        if not job:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Job with job_no {job_no} not found or access denied",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )
       
        
        job.actual_session_end_time = datetime.now()
        
        duration = job.actual_session_end_time - job.actual_session_start_time
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        job.session_duration = f"{hours}:{minutes:02d}:{seconds:02d}"
        
        job.session_completed = True
        job.computed_status = JobStatusEnum.COMPLETED.value
        
        db.commit()
        db.refresh(job)
        
        logger.info(
            f"Session ended for job_no {job_no}. "
            f"Duration: {job.session_duration}"
        )
        
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Session ended successfully",
                "success": True,
                "result": {}
            },
            status_code=status.HTTP_200_OK
        )
        
    except HTTPException:
        raise
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


async def cancel_job(
    job_no: int,
    payload: CancelJobSchema,
    current_user: dict,
    db: Session
) -> JSONResponse:
    try:
        user_entered_by = get_context('entered_by')
        
        job = (
            db.query(Jobs)
            .join(Cases, Jobs.case_no == Cases.case_no)
            .filter(Cases.is_archived == False)
            .filter(Jobs.is_archived == False)
            .filter(Jobs.job_no == job_no)
            .filter(Cases.entered_by == user_entered_by)
            .first()
        )

        if not job:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Job with job_no {job_no} not found or access denied",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        
        logger.info(f"Cancelling job {job_no} with payload: {payload.cancel_reason}")
        
        if payload.cancel_reason:
            job.cancel_reason = payload.cancel_reason
            logger.info(f"Assigned cancel_reason: {payload.cancel_reason} (type: {type(payload.cancel_reason)})")
        else:
            job.cancel_reason = None
            logger.info("Cancel reason set to None")
        
        job.cancel_details = payload.cancel_details
        job.cancel_by = user_entered_by
        job.cancel_date = datetime.now()
        job.computed_status = JobStatusEnum.CANCELLED.value
        
        db.commit()
        db.refresh(job)
        
        logger.info(f"Saved cancel_reason to database: {job.cancel_reason}")
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Job cancelled successfully",
                "success": True,
                "result": {} 
            },
            status_code=status.HTTP_200_OK
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error canceling job {job_no}: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Failed to cancel job",
                "success": False,
                "result": {}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )




async def cancelled_and_completed_jobs(
    type: str,
    start_date: Optional[date],
    end_date: Optional[date],
    page: int,
    page_size: int,
    current_user: dict,
    db: Session
) -> JSONResponse:
    try:
        if type not in ['Cancelled', 'Completed']:
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
        
        user_entered_by = get_context('entered_by')
        logger.info(
            f"Listing {type} jobs for user {user_entered_by} "
            f"(start_date={start_date}, end_date={end_date}, page={page}, page_size={page_size})"
        )
        
        query = (
            db.query(Jobs)
            .join(Cases, Jobs.case_no == Cases.case_no)
            .filter(Cases.is_archived == False)
            .filter(Jobs.is_archived == False)
            .filter(Cases.entered_by == user_entered_by)
            .filter(Jobs.entered_by == user_entered_by)
        )

        if start_date:
            query = query.filter(
                func.date(Jobs.job_date) >= start_date
            )
        if end_date:
            query = query.filter(
                func.date(Jobs.job_date) <= end_date
            )
        
        if type == 'Cancelled':
            query = query.filter(Jobs.computed_status == JobStatusEnum.CANCELLED.value)
        else:
            query = query.filter(
                Jobs.computed_status == JobStatusEnum.COMPLETED.value,
                Jobs.session_completed == True
            )
        
        total = query.count()
        
        jobs = (
            query
            .order_by(Jobs.job_date.desc(), Jobs.job_no.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        
        if not jobs:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": f"No {type} jobs found",
                    "success": True,
                    "result": [],
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total": total,
                        "total_pages": total_pages,
                        "has_next": False,
                        "has_previous": False
                    }
                },
                status_code=status.HTTP_200_OK
            )
        
        jobs_data = [CancelledAndCompletedJobSchema.model_validate(job).model_dump(mode='json') for job in jobs]
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": f"{type} jobs listed successfully",
                "success": True,
                "result": jobs_data,
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
        logger.error(f"Error listing {type} jobs: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to list {type} jobs",
                "success": False,
                "result": []
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



async def mark_job_as_done(
    job_no: int,
    type: str,
    body: dict,
    current_user: dict,
    db: Session
) -> JSONResponse:
    try:
        valid_types = ['case', 'witnesses', 'attorneys', 'billings', 'equipment_time']
        if type not in valid_types:
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
        
        logger.info(f"Marking job {job_no} as done: {type} = {is_done}")
        user_entered_by = get_context('entered_by') 
        
        job = (
            db.query(Jobs)
            .filter(
                Jobs.job_no == job_no,
                Jobs.is_archived == False,
                Jobs.entered_by == user_entered_by
            )
            .first()
        )
        
        if not job:
            logger.warning(f'Job {job_no} not found for user {user_entered_by}')
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Job not found or access denied",
                    "success": False,
                    "result": {}
                },
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        setattr(job, f"mark_is_done_{type}", is_done)
        db.commit()
        db.refresh(job)
        
        logger.info(f'Job {job_no} marked as done: {type} = {is_done}')
        
        message = f"Job {job_no} {type} marked as done successfully" if is_done else f"Job {job_no} {type} marked as not done successfully"
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
        
    except HTTPException:
        raise
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




def _get_calendar_events_query(
    db: Session,
    user_entered_by: int,
    start_date: date,
    end_date: date
) -> List[Jobs]:
    return (
        db.query(Jobs)
        .join(Cases, Jobs.case_no == Cases.case_no)
        .options(joinedload(Jobs.case))
        .filter(Cases.is_archived == False)
        .filter(Jobs.is_archived == False)
        .filter(Jobs.entered_by == user_entered_by)
        .filter(Cases.entered_by == user_entered_by)
        .filter(
            func.date(Jobs.job_date) >= start_date,
            func.date(Jobs.job_date) <= end_date
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
        user_entered_by = get_context('entered_by')
        start_date_filter: date
        end_date_filter: date
        filter_type: str = ""
        if year is not None and month is not None and day is not None:
            if not (1 <= month <= 12):
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
                return JSONResponse(
                    content={
                        "status_code": status.HTTP_400_BAD_REQUEST,
                        "message": f"Invalid date: {str(e)}",
                        "success": False,
                        "result": []
                    },
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            logger.info(f"Week view: Year: {year}, Month: {month}, Day: {day}, Start date: {start_date}, End date: {end_date}")
            start_date_filter, end_date_filter = get_date_range_for_week(year, month, day)
            logger.info(f"Start date: {start_date_filter}, End date: {end_date_filter}")
            filter_type = f"week containing {target_date}"
            logger.info(f"Fetching calendar events for week containing {target_date} for user {user_entered_by}")
            
        elif year is not None and month is not None:
            if not (1 <= month <= 12):
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
            logger.info(f"Fetching calendar events for month {year}-{month:02d} for user {user_entered_by}")
            
        elif start_date is not None and end_date is not None:
            if start_date > end_date:
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
            logger.info(f"Fetching calendar events from {start_date} to {end_date} for user {user_entered_by}")
            
        else:
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
        
        jobs = _get_calendar_events_query(db, user_entered_by, start_date_filter, end_date_filter)
        
        events = [job_to_calendar_event(job, db).model_dump(mode='json') for job in jobs]
        logger.info(f"Events: {events}")
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
