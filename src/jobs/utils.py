"""
Utility functions for jobs module
"""
from typing import Optional, Tuple, Dict, List, Union
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, case, String

from src.jobs.models import Jobs
from src.witness_videos.models import WitnessVideos
from src.jobs.schema import CalendarEventSchema
from src.witnesses.models import Witnesses


def format_time_for_calendar(time_obj) -> str:
    if isinstance(time_obj, str):
        if ':' in time_obj:
            parts = time_obj.split(':')
            return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"
        return time_obj
    elif hasattr(time_obj, 'hour') and hasattr(time_obj, 'minute'):
        return f"{time_obj.hour:02d}:{time_obj.minute:02d}"
    return "00:00"


def get_video_upload_status(
    job_no: Union[int, List[int]],
    db: Session,
) -> Union[Dict[str, Dict[str, str]], Dict[int, Dict[str, Dict[str, str]]]]:
    is_single = isinstance(job_no, int)
    job_nos = [job_no] if is_single else job_no
    
    if not job_nos:
        return {} if not is_single else {"witness_videos_status": {}}
    
    query = (
        db.query(
            Witnesses.job_no,
            Witnesses.witness_name,
            func.count(WitnessVideos.id).label('total_count'),
            func.sum(
                case(
                    (
                        (WitnessVideos.file_path.isnot(None)) &
                        (WitnessVideos.file_path != ""),
                        1
                    ),
                    else_=0
                )
            ).label('uploaded_count')
        )
        .outerjoin(
            WitnessVideos,
            (WitnessVideos.wit_no == Witnesses.id) &
            (WitnessVideos.job_no == Witnesses.job_no) &
            (WitnessVideos.is_archived == False)
        )
        .filter(
            Witnesses.job_no.in_(job_nos),
            Witnesses.is_archived == False
        )
        .group_by(Witnesses.job_no, Witnesses.id, Witnesses.witness_name)
        .all()
    )
    
    if is_single:
        witness_statuses: Dict[str, str] = {}
        for _, witness_name, total_count, uploaded_count in query:
            total_count = total_count or 0
            uploaded_count = uploaded_count or 0
            if total_count > 0 and uploaded_count < total_count:
                witness_statuses[witness_name] = f"{uploaded_count}/{total_count}"
        return {"witness_videos_status": witness_statuses}
    else:
        status_by_job: Dict[int, Dict[str, Dict[str, str]]] = {}
        for job_no, witness_name, total_count, uploaded_count in query:
            if job_no not in status_by_job:
                status_by_job[job_no] = {"witness_videos_status": {}}
            total_count = total_count or 0
            uploaded_count = uploaded_count or 0
            if total_count > 0 and uploaded_count < total_count:
                status_by_job[job_no]["witness_videos_status"][witness_name] = f"{uploaded_count}/{total_count}"
        for job_no in job_nos:
            if job_no not in status_by_job:
                status_by_job[job_no] = {"witness_videos_status": {}}
        return status_by_job


def build_calendar_event_title(job: Jobs) -> str:
    case_name = "Unknown Case"
    location = ""
    
    if job.case:
        if job.case.case_short_name:
            case_name = job.case.case_short_name
        elif job.case.case_full_name:
            case_name = job.case.case_full_name
    
    if job.job_loc_name:
        location = f" - {job.job_loc_name}"
    
    return f"{job.case.case_type if job.case and job.case.case_type else ''}: {case_name}{location}"


def job_to_calendar_event(job: Jobs, db: Session) -> CalendarEventSchema:
    witness_videos_status = get_video_upload_status(job.job_no, db)
    title = build_calendar_event_title(job)
    status = None
    
    start_time_str = format_time_for_calendar(job.start_time)
    end_time_str = format_time_for_calendar(job.end_time)
    
    deadline = job.video_upload_deadline
    
    return CalendarEventSchema(
        id=job.job_no,
        case_id=job.case.id,
        title=title,
        date=job.job_date,
        startTime=start_time_str,
        endTime=end_time_str,
        status=status,
        computed_status=job.computed_status,
        deadline=deadline,
        type= job.case.case_type if job.case and job.case.case_type else '',
        witness_videos_status=witness_videos_status.get("witness_videos_status",{})
    )


def get_date_range_for_month(year: int, month: int) -> Tuple[date, date]:
    start_date = date(year, month, 1)
    
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    return start_date, end_date


def get_date_range_for_week(year: int, month: int, day: int) -> Tuple[date, date]:
    target_date = date(year, month, day)
    
    days_since_monday = target_date.weekday()
    start_date = target_date - timedelta(days=days_since_monday)
    
    end_date = start_date + timedelta(days=6)
    
    return start_date, end_date

