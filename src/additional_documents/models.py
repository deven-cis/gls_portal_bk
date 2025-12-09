from sqlalchemy import Column, DateTime, ForeignKey, Time, Integer, String, Text, Boolean
from src.core.models import Base
from sqlalchemy.orm import relationship

class AdditionalDocuments(Base):
    __tablename__ = "additional_documents"

    job_no = Column(Integer, ForeignKey("jobs.job_no"), nullable=False, index=True)
    billing_id = Column(Integer, ForeignKey("billings.id"), nullable=True, index=True)
    equipment_time_id = Column(Integer, ForeignKey("equipment_time.id"), nullable=True, index=True)
    file_name = Column(Text, nullable=True)
    file_path = Column(Text, nullable=True)

    # Define the relationships to the other models
    job = relationship("Jobs", back_populates="additional_documents")
    billing = relationship("Billings", back_populates="additional_documents")
    equipment_time = relationship("EquipmentTime", back_populates="additional_documents")
