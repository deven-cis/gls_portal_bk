from sqlalchemy import Column, DateTime, Time, Integer, String, BigInteger
from sqlalchemy.types import Text
from src.core.models import Base
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
import enum


class CancelReasonEnum(enum.Enum):
    HEARING_RESCHEDULED = "Hearing rescheduled"
    WITNESS_ABSENT = "Witness absent"
    ATTORNEY_ABSENT = "Attorney absent"
    JUDGE_ABSENT = "Judge Absent"


class Jobs(Base):
    job_date = Column(DateTime, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    timezone_no = Column(Integer, nullable=True)
    status = Column(String(255), nullable=False)
    case_no = Column(Integer, nullable=False)
    job_type = Column(String(255), nullable=True)
    scheduled_by_email = Column(String(255), nullable=True)
    job_loc_name = Column(String(255), nullable=True)
    job_loc_address = Column(String(255), nullable=True)
    job_loc_city = Column(String(255), nullable=True)
    job_loc_state = Column(String(255), nullable=True)
    job_loc_zip = Column(String(255), nullable=True)
    scheduling_notes_html = Column(String, nullable=True)
    zoom_meeting_id = Column(BigInteger, nullable=True)
    confirmation_notes_html = Column(String, nullable=True)
    cancel_by = Column(Integer, nullable=True)
    cancel_date = Column(DateTime, nullable=True)
    job_no = Column(Integer, nullable=True)
    cancel_details = Column(Text, nullable=True)
    cancel_resone = Column(
        PgEnum(CancelReasonEnum, name="cancel_reason_enum"),
        nullable=True
    )