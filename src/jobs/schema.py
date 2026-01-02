from datetime import datetime, time
from typing import Optional, List

from pydantic import BaseModel
from src.cases.schema import CaseSchema, CaseListSchema
from src.jobs.models import CancelReasonEnum, JobStatusEnum
from src.witnesses.schema import WitnessSchema
from src.attorneys.schema import AttorneySchema

class JobSchema(BaseModel):
    id: int
    job_date: datetime
    start_time: time
    end_time: time
    timezone_no: Optional[int] = None
    status: Optional[str] = None
    case_no: int
    job_type: Optional[str] = None
    scheduled_by_email: Optional[str] = None
    job_loc_name: Optional[str] = None
    job_loc_address: Optional[str] = None
    job_loc_city: Optional[str] = None
    job_loc_state: Optional[str] = None
    job_loc_zip: Optional[str] = None
    zoom_meeting_id: Optional[int] = None
    job_no: Optional[int] = None
    computed_status: Optional[str] = None
    mark_is_done: Optional[bool] = None
    cancel_reason: Optional[CancelReasonEnum] = None
    cancel_details: Optional[str] = None
    case: Optional[CaseListSchema] = None

    class Config:
        from_attributes = True

class CancelJobSchema(BaseModel):
    cancel_reason: Optional[CancelReasonEnum] = None
    cancel_details: Optional[str] = None

    class Config:
        from_attributes = True

class CancelledAndCompletedJobSchema(BaseModel):
    job_no: int
    job_date: datetime
    start_time: time
    job_loc_name: Optional[str] = None
    job_loc_address: Optional[str] = None
    job_loc_city: Optional[str] = None
    job_loc_state: Optional[str] = None
    job_loc_zip: Optional[str] = None
    case: Optional[CaseListSchema] = None
    computed_status: Optional[JobStatusEnum] = None

    class Config:
        from_attributes = True

class CompletedJobDetailsSchema(BaseModel):
    job_no: int
    job_date: datetime
    start_time: time
    end_time: time
    job_loc_name: Optional[str] = None
    job_loc_address: Optional[str] = None
    job_loc_city: Optional[str] = None
    job_loc_state: Optional[str] = None
    job_loc_zip: Optional[str] = None
    case: Optional[CaseListSchema] = None
    computed_status: Optional[str] = None
    witnesses: List[WitnessSchema] = []
    attorneys: List[AttorneySchema] = []

    class Config:
        from_attributes = True


class CalendarEventSchema(BaseModel):
    """Schema for calendar events matching frontend requirements"""
    id: int  # job_no
    case_id: int  # case.id
    title: str
    date: datetime
    startTime: str  # Format: "HH:MM"
    endTime: str  # Format: "HH:MM"
    status: Optional[str] = None  # "pending" if videos are pending
    videosUploaded: Optional[int] = None
    totalVideos: Optional[int] = None
    deadline: Optional[datetime] = None
    type: str = "deposition"
    hasVideo: bool = False

    class Config:
        from_attributes = True
    
class MarkJobAsDoneSchema(BaseModel):
    job_no: int
    mark_is_done_case: Optional[bool] = False
    mark_is_done_witnesses: Optional[bool] = False
    mark_is_done_attorneys: Optional[bool] = False
    mark_is_done_billings: Optional[bool] = False
    mark_is_done_equipment_time: Optional[bool] = False

    class Config:
        from_attributes = True