from sqlalchemy import Column, DateTime, Time, Integer, String, BigInteger, ForeignKey, Boolean, Date, Numeric, LargeBinary
from sqlalchemy.types import Text
from sqlalchemy.orm import relationship
from src.core.models import Base
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
import enum


class JobsTasks(Base):
    __tablename__ = "jobs_tasks"    
    
    task_no = Column(Integer, unique=True, index=True, nullable=False)
    job_no = Column(Integer, ForeignKey('jobs.job_no', ondelete="CASCADE"), nullable=False)
    rsrc_no = Column(Integer, ForeignKey('resources.rsrc_no'), nullable=True)
    task_list_note = Column(String(1024), nullable=True)
    notified_date = Column(DateTime, nullable=True)
    order_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    cancel_date = Column(DateTime, nullable=True)
    acknowledged_date = Column(DateTime, nullable=True)
    estimated_delivery_date = Column(Date, nullable=True)
    turn_in_date = Column(DateTime, nullable=True)
    cancel_by = Column(Integer, nullable=True)
    estimated_pages = Column(Integer, nullable=True)
    task_notes = Column(Text, nullable=True)
    rsrc_notes = Column(Text, nullable=True)

    # Relationships
    job = relationship(
        "Jobs",
        foreign_keys=[job_no],
        primaryjoin="JobsTasks.job_no == Jobs.job_no",
        back_populates="tasks"
    )

    rsrc = relationship(
        "Resources",
        foreign_keys=[rsrc_no],
        primaryjoin="JobsTasks.rsrc_no == Resources.rsrc_no",
        back_populates="tasks"
    )