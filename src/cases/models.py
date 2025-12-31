from sqlalchemy import Column, String, DateTime, Integer, Boolean, Float
from sqlalchemy.orm import relationship

from src.core.models import Base


class Cases(Base):
    case_short_name = Column(String, nullable=True)
    case_full_name = Column(String, nullable=True)
    case_type = Column(String, nullable=True)
    status = Column(String, nullable=True)
    trial_date = Column(DateTime, nullable=True)
    case_no = Column(Integer, unique=True, nullable=False)
    case_number = Column(Integer, nullable=True)
    mark_is_done = Column(Boolean, default=False)
    # Case progress tracking fields
    progress_percentage = Column(Float, nullable=True)
    total_jobs = Column(Integer, nullable=True)
    completed_jobs = Column(Integer, nullable=True)
    case_status = Column(String(50), nullable=True)

    # Reverse relationship to access jobs from a case
    # Join condition is inferred from Jobs.case_no ForeignKey
    jobs = relationship(
        "Jobs",
        back_populates="case",
        lazy="select",
    )