from sqlalchemy import Column, ForeignKey, Text, Time, Integer, String
from sqlalchemy.orm import relationship

from src.core.models import Base
from src.witnesses.models import Witnesses


class WitnessVideos(Base):
    __tablename__ = "witness_videos"

    wit_no = Column(Integer, ForeignKey("witnesses.id", ondelete="CASCADE"), nullable=False)
    job_no = Column(Integer, ForeignKey("jobs.job_no"), nullable=False)
    start_time = Column(String(255), nullable=True)
    end_time = Column(String(255), nullable=True)
    file_name = Column(Text, nullable=True)
    file_path = Column(Text, nullable=True)

    # Relationship back to Witnesses
    witness = relationship(
        "Witnesses",
        back_populates="witness_vid"
    )
    