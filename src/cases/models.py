from sqlalchemy import Column, String, DateTime

from src.core.models import Base


class Cases(Base):
    case_short_name = Column(String, nullable=True)
    case_full_name = Column(String, nullable=True)
    case_type = Column(String, nullable=True)
    status = Column(String, nullable=True)
    trial_date = Column(DateTime, nullable=True)
