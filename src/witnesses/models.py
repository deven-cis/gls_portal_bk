from sqlalchemy import Column, DateTime, ForeignKey, Time, Integer, String, Text, Boolean, BigInteger, Numeric
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
     # ── Video merge fields ──────────────────────────────────────────
    merged_video_path  = Column(Text, nullable=True)
    merged_video_name  = Column(Text, nullable=True)
    merged_video_size  = Column(BigInteger, nullable=True)
    merged_duration    = Column(Numeric(10, 2), nullable=True)
    merge_status       = Column(String(50), nullable=True, default="pending")
    merge_error        = Column(Text, nullable=True)
    merge_requested_at = Column(DateTime, nullable=True)
    merge_completed_at = Column(DateTime, nullable=True)

    job = relationship("Jobs", back_populates="witnesses")

    witness_vid = relationship(
            "WitnessVideos",
            back_populates="witness",
            cascade="all, delete-orphan"
        )

