from decimal import Decimal
from sqlalchemy import Column, Time, Integer, Boolean, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from src.core.models import Base


class EquipmentTime(Base):
    __tablename__ = "equipment_time"

    job_no = Column(Integer, ForeignKey("jobs.job_no"), nullable=False, index=True)
    laptop_used = Column(Boolean, default=False)
    pip_used = Column(Boolean, default=False)
    exhibit_tech = Column(Boolean, default=False)
    parking_cost = Column(Numeric(10, 2), default=Decimal('0.00'), server_default='0.00')
    time_after = Column(Time, nullable=True)

    # Define the relationship to the Jobs model
    job = relationship("Jobs", back_populates="equipment_time")
    
    additional_documents = relationship(
        "AdditionalDocuments",
        back_populates="equipment_time",
        cascade="all, delete-orphan"
    )
