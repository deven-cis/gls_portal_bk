from sqlalchemy import Column, Integer, String, Text, BigInteger, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from src.core.models import Base


class UploadedVideos(Base):
    __tablename__ = "uploaded_videos"

    upload_id = Column(String(64), nullable=False, unique=True, index=True)
    original_file_name = Column(Text, nullable=False)
    stored_file_name = Column(Text, nullable=True)
    content_type = Column(String(255), nullable=True)
    file_ext = Column(String(20), nullable=False)

    temp_file_path = Column(Text, nullable=True)
    final_file_path = Column(Text, nullable=True)
    multipart_upload_id = Column(Text, nullable=True)
    multipart_object_key = Column(Text, nullable=True)
    upload_strategy = Column(String(50), nullable=True)

    expected_file_size = Column(BigInteger, nullable=True)
    bytes_received = Column(BigInteger, nullable=True, default=0)
    total_chunks = Column(Integer, nullable=True)
    received_chunks = Column(Integer, nullable=True, default=0)

    file_size = Column(BigInteger, nullable=True)
    duration_seconds = Column(Numeric(10, 2), nullable=True)
    timecode = Column(Text, nullable=True)
    format_name = Column(Text, nullable=True)

    status = Column(String(50), nullable=False, default="initialized")
    expires_at = Column(DateTime, nullable=True, index=True)
    attached_at = Column(DateTime, nullable=True)
    witness_video_id = Column(Integer, ForeignKey("witness_videos.id", ondelete="SET NULL"), nullable=True, index=True)

    witness_video = relationship("WitnessVideos")
