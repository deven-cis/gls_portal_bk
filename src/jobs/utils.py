"""
Utility functions for jobs module
"""
from typing import Optional, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.jobs.models import Jobs
from src.witness_videos.models import WitnessVideos
from src.jobs.schema import CalendarEventSchema
from src.cases.models import Cases


def format_time_for_calendar(time_obj) -> str:
    """
    Format time object to "HH:MM" string format for calendar.
    
    Args:
        time_obj: datetime.time or string time
        
    Returns:
        str: Time in "HH:MM" format
    """
    if isinstance(time_obj, str):
        # If it's already a string, try to parse it
        if ':' in time_obj:
            parts = time_obj.split(':')
            return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"
        return time_obj
    elif hasattr(time_obj, 'hour') and hasattr(time_obj, 'minute'):
        return f"{time_obj.hour:02d}:{time_obj.minute:02d}"
    return "00:00"


def get_video_upload_status(
    job_no: int,
    db: Session,
    expected_count: Optional[int] = None
) -> dict:
    """
    Get video upload status for a job.
    
    Args:
        job_no: Job number
        db: Database session
        expected_count: Expected video count (from job.expected_video_count)
        
    Returns:
        dict with keys:
            - videos_uploaded: int
            - total_videos: int
            - has_video: bool
            - is_pending: bool
    """
    # Count uploaded videos (non-archived)
    videos_uploaded = (
        db.query(func.count(WitnessVideos.id))
        .filter(
            WitnessVideos.job_no == job_no,
            WitnessVideos.is_archived == False,
            WitnessVideos.file_path.isnot(None),
            WitnessVideos.file_path != ""
        )
        .scalar() or 0
    )
    
    # Use expected count if provided, otherwise count witnesses
    if expected_count is not None and expected_count > 0:
        total_videos = expected_count
    else:
        # Fallback: count witnesses for the job
        from src.witnesses.models import Witnesses
        total_videos = (
            db.query(func.count(Witnesses.id))
            .filter(
                Witnesses.job_no == job_no,
                Witnesses.is_archived == False
            )
            .scalar() or 0
        )
    
    has_video = videos_uploaded > 0
    is_pending = total_videos > 0 and videos_uploaded < total_videos
    
    return {
        "videos_uploaded": videos_uploaded,
        "total_videos": total_videos,
        "has_video": has_video,
        "is_pending": is_pending
    }


def build_calendar_event_title(job: Jobs) -> str:
    """
    Build calendar event title from job and case information.
    
    Args:
        job: Jobs model instance
        
    Returns:
        str: Formatted title like "Deposition: Johnson vs. Smith - Courtroom"
    """
    case_name = "Unknown Case"
    location = ""
    
    if job.case:
        if job.case.case_short_name:
            case_name = job.case.case_short_name
        elif job.case.case_full_name:
            case_name = job.case.case_full_name
    
    if job.job_loc_name:
        location = f" - {job.job_loc_name}"
    
    return f"Deposition: {case_name}{location}"


def job_to_calendar_event(job: Jobs, db: Session) -> CalendarEventSchema:
    """
    Convert a Jobs model instance to CalendarEventSchema.
    
    Args:
        job: Jobs model instance
        db: Database session for querying video status
        
    Returns:
        CalendarEventSchema: Calendar event data
    """
    # Get video upload status
    video_status = get_video_upload_status(
        job.job_no,
        db,
        expected_count=job.expected_video_count
    )
    
    # Build title
    title = build_calendar_event_title(job)
    
    # Determine status
    status = None
    if video_status["is_pending"]:
        status = "pending"
    
    # Format times
    start_time_str = format_time_for_calendar(job.start_time)
    end_time_str = format_time_for_calendar(job.end_time)
    
    # Get deadline if exists
    deadline = job.video_upload_deadline
    
    return CalendarEventSchema(
        id=job.job_no,
        case_id=job.case.id,
        title=title,
        date=job.job_date,
        startTime=start_time_str,
        endTime=end_time_str,
        status=status,
        videosUploaded=video_status["videos_uploaded"] if video_status["total_videos"] > 0 else None,
        totalVideos=video_status["total_videos"] if video_status["total_videos"] > 0 else None,
        deadline=deadline,
        type="deposition",
        hasVideo=video_status["has_video"]
    )


def get_date_range_for_month(year: int, month: int) -> Tuple[date, date]:
   
    # First day of the month
    start_date = date(year, month, 1)
    
    # Last day of the month
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    return start_date, end_date


def get_date_range_for_week(year: int, month: int, day: int) -> Tuple[date, date]:
    target_date = date(year, month, day)
    
    # Get Monday of the week (weekday 0 = Monday)
    days_since_monday = target_date.weekday()
    start_date = target_date - timedelta(days=days_since_monday)
    
    # Get Sunday of the week
    end_date = start_date + timedelta(days=6)
    
    return start_date, end_date

