from decimal import Decimal
from sqlalchemy import Column, Time, Integer, Boolean, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship
from src.core.models import Base


class EquipmentTime(Base):
    __tablename__ = "equipment_time"

    job_no = Column(Integer, ForeignKey("jobs.job_no", ondelete="CASCADE"), nullable=False, index=True)
    laptop_used = Column(Boolean, default=False)
    pip_used = Column(Boolean, default=False)
    exhibit_tech = Column(Boolean, default=False)
    parking_cost = Column[Decimal](Numeric(10, 2), default=Decimal('0.00'), server_default='0.00')
    time_after = Column(Time, nullable=True)
    camera_captured_file_name = Column(Text, nullable=True)
    camera_captured_file_path = Column(Text, nullable=True)

    job = relationship("Jobs", back_populates="equipment_time")

    additional_documents = relationship(
        "AdditionalDocuments",
        back_populates="equipment_time",
        cascade="all, delete-orphan"
    )