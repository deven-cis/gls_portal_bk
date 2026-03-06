from sqlalchemy import Column, Integer, ForeignKey, DateTime, String, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from src.core.models import Base


class JobAssignment(Base):
    __tablename__ = "job_assignments"
    
    # The resource who assigned/reassigned the job task
    assigner_id = Column(Integer, ForeignKey('resources.rsrc_no'), nullable=False)
    # The resource who received the assignment
    assignee_id = Column(Integer, ForeignKey('resources.rsrc_no'), nullable=False)

    # The job task being assigned (references jobs_tasks.task_no)
    job_task_no = Column(Integer, ForeignKey('jobs_tasks.task_no'), nullable=False)

    # The case number (for quick filtering without joining jobs_tasks table)
    case_no = Column(Integer, ForeignKey('cases.case_no'), nullable=True)

    # Reason for reassignment (from the confirmation dialog)
    reason = Column(Text, nullable=True)

    # Relationships - using back_populates for explicit bidirectional relationships
    assigner = relationship(
        "Resources",
        foreign_keys=[assigner_id],
        backref="job_assignments_assigned_by_me"
    )

    assignee = relationship(
        "Resources",
        foreign_keys=[assignee_id],
        backref="job_assignments_assigned_to_me"
    )

    job_task = relationship(
        "JobsTasks",
        foreign_keys=[job_task_no],
        primaryjoin="JobAssignment.job_task_no == JobsTasks.task_no",
        backref="assignments"
    )

    case = relationship(
        "Cases",
        backref="job_assignments"
    )
    