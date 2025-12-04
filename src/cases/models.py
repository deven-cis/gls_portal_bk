from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.orm import relationship

from src.core.models import Base


class Cases(Base):
    case_short_name = Column(String, nullable=True)
    case_full_name = Column(String, nullable=True)
    case_type = Column(String, nullable=True)
    status = Column(String, nullable=True)
    trial_date = Column(DateTime, nullable=True)
    case_no = Column(Integer, nullable=True)

    # Reverse relationship to access jobs from a case
    # Join condition is inferred from Jobs.case_no ForeignKey
    jobs = relationship(
        "Jobs",
        back_populates="case",
        lazy="select",
    )