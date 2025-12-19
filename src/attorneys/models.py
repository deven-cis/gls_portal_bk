from sqlalchemy import Column, DateTime, ForeignKey, Time, Integer, String, Text, Boolean
from src.core.models import Base
from sqlalchemy.orm import relationship


class Attorneys(Base):
    __tablename__ = "attorneys"

    job_no = Column(Integer, ForeignKey("jobs.job_no"), nullable=False, index=True)
    attorney_name = Column(String(255), nullable=False)
    firm_name = Column(String(255), nullable=False)
    notes = Column(Text, nullable=False)
    order_details = Column(Text, nullable=False)
    file_name = Column(Text, nullable=True)
    file_name_path = Column(Text, nullable=True)
    mark_is_done = Column(Boolean, default=False)

    # Define the relationship to the Jobs model
    job = relationship("Jobs", back_populates="attorneys")  
