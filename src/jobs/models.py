from sqlalchemy import Column, DateTime, Time, Integer, String, BigInteger, ForeignKey
from sqlalchemy.types import Text
from sqlalchemy.orm import relationship
from src.core.models import Base
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
import enum

# Ensure Cases model is registered before SQLAlchemy configures Jobs
# (avoid circular import by importing near top without referencing Jobs there)
from src.cases.models import Cases 


class CancelReasonEnum(enum.Enum):
    HEARING_RESCHEDULED = "Hearing rescheduled"
    WITNESS_ABSENT = "Witness absent"
    ATTORNEY_ABSENT = "Attorney absent"
    JUDGE_ABSENT = "Judge Absent"


class JobStatusEnum(enum.Enum):
    UPCOMING = "upcoming"
    SESSION_NOT_STARTED = "session_not_started"
    SESSION_IN_PROGRESS = "session_in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Jobs(Base):
    __tablename__ = "jobs"

    job_date = Column(DateTime, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    timezone_no = Column(Integer, nullable=True)
    status = Column(String(255), nullable=False)
    case_no = Column(Integer, ForeignKey('cases.case_no'), nullable=False)
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
    computed_status = Column(String(50), nullable=True, default="upcoming")

    # Many-to-one: each job belongs to a single case
    # Let SQLAlchemy infer the join from the ForeignKey on `case_no`
    case = relationship(
        Cases,
        back_populates="jobs",
        lazy="joined",
    )