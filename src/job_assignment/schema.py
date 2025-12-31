from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class JobAssignmentCreateSchema(BaseModel):
    """Schema for creating a new job assignment"""
    assignee_id: int
    job_no: int  # References jobs.job_no (business identifier)
    case_no: Optional[int] = None
    reason: Optional[str] = None


class JobAssignmentResponseSchema(BaseModel):
    """Schema for job assignment response"""
    id: int
    assigner_id: int
    assignee_id: int
    job_no: int  # References jobs.job_no (business identifier)
    case_no: Optional[int] = None
    entered_at: Optional[datetime] = None  # When the assignment was created (from Base)
    reason: Optional[str] = None
    
    class Config:
        from_attributes = True


class JobReassignSchema(BaseModel):
    """Schema for reassigning a job to another user"""
    assignee_id: int  # New user to assign the job to
    reason: str  # Required reason for reassignment


class JobReassignRequestSchema(BaseModel):
    """Schema for frontend reassign job request"""
    assignee_user_id: int        
    assignee_entered_by: int     
    job_id: int         
    reason: str         
