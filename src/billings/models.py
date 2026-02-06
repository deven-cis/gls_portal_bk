from sqlalchemy import Column, ForeignKey, Time, Integer, Text, Boolean, String

from src.core.models import Base
from sqlalchemy.orm import relationship



class Billings(Base):
    __tablename__ = "billings"

    job_no = Column(Integer, ForeignKey("jobs.job_no", ondelete="CASCADE"), nullable=False, index=True)
    cancel_en_route = Column(Boolean, default=False)
    cancel_setup = Column(Boolean, default=False)
    billing_notes = Column(Text, nullable=True)
    videographer_hours_present = Column(String(255), nullable=True)
    file_hours_length = Column(String(255), nullable=True)
    camera_captured_file_name = Column(Text, nullable=True)
    camera_captured_file_path = Column(Text, nullable=True)

    # Define the relationship to the Jobs model
    job = relationship("Jobs", back_populates="billing")

    additional_documents = relationship(
        "AdditionalDocuments",
        back_populates="billing",
        cascade="all, delete-orphan"
    )