from sqlalchemy import Column, DateTime, Time, Integer, String, BigInteger

from src.core.models import Base


class Witnesses(Base):
    jod_no = Column(Integer, nullable=False)
    witness_name = Column(String(255), nullable=False)
    witness_email = Column(String(255), nullable=True)
    actual_start_time = Column(Time, nullable=True)
    actual_end_time = Column(Time, nullable=True)
    read_sign_date = Column(DateTime, nullable=True)
    read_sign_to = Column(Integer, nullable=True)
    wit_no = Column(Integer, nullable=True)
    