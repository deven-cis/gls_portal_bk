from sqlalchemy import Column, ForeignKey, Text, Time, Integer, BigInteger, Numeric
from sqlalchemy.orm import relationship

from src.core.models import Base

class WitnessVideos(Base):
    __tablename__ = "witness_videos"

    wit_no = Column(Integer, ForeignKey("witnesses.id", ondelete="CASCADE"), nullable=False, index=True)
    job_no = Column(Integer, ForeignKey("jobs.job_no", ondelete="CASCADE"), nullable=False, index=True)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    file_name = Column(Text, nullable=True)
    file_path = Column(Text, nullable=True)

    # ── New metadata fields ─────────────────────────────────────────
    file_size        = Column(BigInteger, nullable=True)       # size in bytes
    duration_seconds = Column(Numeric(10, 2), nullable=True)   # from ffprobe in seconds
    timecode         = Column(Text, nullable=True)             # auto if camera embedded

    # Relationship back to Witnesses
    witness = relationship(
        "Witnesses",
        back_populates="witness_vid"
    )
    