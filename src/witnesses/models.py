from sqlalchemy import Column, DateTime, ForeignKey, Time, Integer, String, Text, Boolean

from src.core.models import Base
from sqlalchemy.orm import relationship


class Witnesses(Base):
    job_no = Column(Integer, ForeignKey("jobs.job_no", ondelete="CASCADE"), nullable=False, index=True)
    witness_name = Column(String(255), nullable=False)
    witness_email = Column(String(255), nullable=True)
    actual_start_time = Column(Time, nullable=True)
    actual_end_time = Column(Time, nullable=True)
    read_sign_date = Column(DateTime, nullable=True)
    read_sign_to = Column(Integer, nullable=True)
    wit_no = Column(Integer, nullable=True)
    read_on_text = Column(Text, nullable=True)
    read_on_time = Column(Time, nullable=True)
    read_off_text = Column(Text, nullable=True)
    read_off_time = Column(Time, nullable=True)

    job = relationship("Jobs", back_populates="witnesses")

    witness_vid = relationship(
            "WitnessVideos",
            back_populates="witness",
            cascade="all, delete-orphan"
        )

