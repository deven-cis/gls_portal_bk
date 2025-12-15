from datetime import time
from sqlalchemy import Column, DateTime, ForeignKey, Time, Integer, String, Text

from src.core.models import Base
from sqlalchemy.orm import relationship


class Witnesses(Base):
    job_no = Column(Integer, ForeignKey("jobs.job_no", ondelete="CASCADE"), nullable=False)
    witness_name = Column(String(255), nullable=False)
    witness_email = Column(String(255), nullable=True)
    actual_start_time = Column(Time, nullable=True)
    actual_end_time = Column(Time, nullable=True)
    read_sign_date = Column(DateTime, nullable=True)
    read_sign_to = Column(Integer, nullable=True)
    wit_no = Column(Integer, nullable=True, unique=True)
    read_on_text = Column(Text, nullable=False)
    read_on_time = Column(Time, nullable=False)
    read_off_text = Column(Text, nullable=False)
    read_off_time = Column(Time, nullable=False)

    job = relationship("Jobs", back_populates="witnesses")

    witness_vid = relationship(
            "WitnessVideos",
            back_populates="witness",
            cascade="all, delete-orphan"
        )

    def __init__(self, **kwargs):
        # Set defaults for required fields if not provided
        if 'read_on_time' not in kwargs:
            kwargs['read_on_time'] = time(0, 0, 0)
        if 'read_off_time' not in kwargs:
            kwargs['read_off_time'] = time(0, 0, 0)
        super().__init__(**kwargs)