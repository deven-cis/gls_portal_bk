from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.orm import relationship
from src.core.models import Base


class Cases(Base):
    case_short_name = Column(String, nullable=True)
    case_full_name = Column(String, nullable=True)
    case_type = Column(String, nullable=True)
    status = Column(String, nullable=True)
    trial_date = Column(DateTime, nullable=True)
    case_no = Column(Integer, unique=True, nullable=False, index=True)
    case_number = Column(String(255), nullable=True)
    case_status = Column(String(50), nullable=True)

    jobs = relationship(
        "Jobs",
        back_populates="case",
        lazy="select"
    )