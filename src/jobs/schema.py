from datetime import datetime, time
from typing import Optional

from pydantic import BaseModel
from src.cases.schema import CaseSchema

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
    scheduling_notes_html: Optional[str] = None
    zoom_meeting_id: Optional[int] = None
    confirmation_notes_html: Optional[str] = None
    cancel_by: Optional[int] = None
    cancel_date: Optional[datetime] = None
    job_no: Optional[int] = None
    cancel_details: Optional[str] = None
    cancel_resone: Optional[str] = None
    entered_at: Optional[datetime] = None
    last_modified_at: Optional[datetime] = None
    entered_by: Optional[int] = None
    last_modified_by: Optional[int] = None
    computed_status: Optional[str] = None
    case: Optional[CaseSchema] = None

    class Config:
        orm_mode = True