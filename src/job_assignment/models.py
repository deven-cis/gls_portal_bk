from sqlalchemy import Column, Integer, ForeignKey, DateTime, String, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from src.core.models import Base


class JobAssignment(Base):
    __tablename__ = "job_assignments"
    
    # The user who assigned/reassigned the job
    assigner_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    # The user who received the assignment
    assignee_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # The job being assigned (references jobs.job_no - the business identifier)
    job_no = Column(Integer, ForeignKey('jobs.job_no'), nullable=False)
    
    # The case number (for quick filtering without joining jobs table)
    case_no = Column(Integer, ForeignKey('cases.case_no'), nullable=True)
    
    # Reason for reassignment (from the confirmation dialog)
    reason = Column(Text, nullable=True)

    
    # Relationships - using back_populates for explicit bidirectional relationships
    assigner = relationship(
        "Users",
        foreign_keys=[assigner_id],
        back_populates="jobs_assigned_by_me"
    )
    
    assignee = relationship(
        "Users",
        foreign_keys=[assignee_id],
        back_populates="assigned_jobs"
    )
    
    job = relationship(
        "Jobs",
        back_populates="assignment_history",
        foreign_keys=[job_no],
        primaryjoin="JobAssignment.job_no == Jobs.job_no"
    )
    
    case = relationship(
        "Cases",
        backref="job_assignments"
    )
    