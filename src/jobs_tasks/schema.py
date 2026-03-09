from datetime import datetime, time, date
from typing import Optional, List, Dict

from pydantic import BaseModel, Field
from src.cases.schema import CaseListSchema
from src.jobs.models import CancelReasonEnum, JobStatusEnum
from src.jobs.schema import JobSchema, CancelJobSchema, CancelledAndCompletedJobSchema, CompletedJobDetailsSchema, CalendarEventSchema, MarkJobAsDoneSchema  # Import all needed schemas
from src.witnesses.schema import WitnessSchema
from src.attorneys.schema import AttorneySchema
from src.resources.schema import ResourceResponseSchema

class JobsTaskSchema(JobSchema):  # Inherit from JobSchema to get all job fields
    """JobsTask schema that extends JobSchema with task-specific fields"""
    # JobsTasks fields
    id: int
    task_no: int
    rsrc_no: Optional[int] = None
    task_list_note: Optional[str] = None
    notified_date: Optional[datetime] = None
    order_date: Optional[date] = None
    due_date: Optional[date] = None
    cancel_date: Optional[datetime] = None
    acknowledged_date: Optional[datetime] = None
    estimated_delivery_date: Optional[date] = None
    turn_in_date: Optional[datetime] = None
    cancel_by: Optional[int] = None
    estimated_pages: Optional[int] = None
    task_notes: Optional[str] = None
    rsrc_notes: Optional[str] = None
    
    # Override job_date from JobSchema to use date instead of datetime
    job_date: date
    
    # Relationships
    case: Optional[CaseListSchema] = None
    resource: Optional[ResourceResponseSchema] = None
    witness_videos_status: Optional[Dict[str, str]] = None

    class Config:
        from_attributes = True

class JobsTaskListSchema(JobSchema):
    """JobsTask list schema that inherits from JobSchema"""

    task_no: Optional[int] = None
    rsrc_no: Optional[int] = None
    

    class Config:
        from_attributes = True
        populate_by_name = True

class JobsTaskCreateSchema(BaseModel):
    """Schema for creating new jobstasks"""
    job_no: int
    rsrc_no: Optional[int] = None
    task_list_note: Optional[str] = None
    order_date: Optional[date] = None
    due_date: Optional[date] = None
    estimated_delivery_date: Optional[date] = None
    estimated_pages: Optional[int] = None
    task_notes: Optional[str] = None

    class Config:
        from_attributes = True

class JobsTaskUpdateSchema(BaseModel):
    """Schema for updating existing jobstasks"""
    rsrc_no: Optional[int] = None
    task_list_note: Optional[str] = None
    order_date: Optional[date] = None
    due_date: Optional[date] = None
    estimated_delivery_date: Optional[date] = None
    turn_in_date: Optional[datetime] = None
    estimated_pages: Optional[int] = None
    task_notes: Optional[str] = None
    rsrc_notes: Optional[str] = None

    class Config:
        from_attributes = True

# Use CancelJobSchema from jobs folder instead of defining duplicate
JobsTaskCancelSchema = CancelJobSchema

class JobsTaskSessionSchema(BaseModel):
    """Schema for session management"""
    actual_session_start_time: Optional[datetime] = None
    actual_session_end_time: Optional[datetime] = None
    session_duration: Optional[str] = None
    session_completed: Optional[bool] = None

    class Config:
        from_attributes = True

# Use CalendarEventSchema from jobs folder instead of defining duplicate
JobsTaskCalendarSchema = CalendarEventSchema

# Use MarkJobAsDoneSchema from jobs folder instead of defining duplicate  
MarkJobsTaskAsDoneSchema = MarkJobAsDoneSchema

# Use CompletedJobDetailsSchema from jobs folder for detailed views
JobsTaskDetailsSchema = CompletedJobDetailsSchema

# Use CancelledAndCompletedJobSchema from jobs folder for cancelled/completed views
JobsTaskCancelledAndCompletedSchema = CancelledAndCompletedJobSchema

# Use CompletedJobDetailsSchema from jobs folder for completed job details
JobsTaskCompletedDetailsSchema = CompletedJobDetailsSchema