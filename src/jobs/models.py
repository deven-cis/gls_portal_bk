from sqlalchemy import Column, DateTime, Time, Integer, String, BigInteger, ForeignKey, Boolean, Date
from sqlalchemy.types import Text
from sqlalchemy.orm import relationship
from src.core.models import Base
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
import enum

class CancelReasonEnum(enum.Enum):
    HEARING_RESCHEDULED = "Hearing rescheduled"
    WITNESS_ABSENT = "Witness absent"
    ATTORNEY_ABSENT = "Attorney absent"
    JUDGE_ABSENT = "Judge Absent"


class JobStatusEnum(enum.Enum):
    SCHEDULED = "Scheduled"
    SESSION_NOT_STARTED = "Session not started"
    SESSION_IN_PROGRESS = "Session Started"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


class Jobs(Base):
    __tablename__ = "jobs"

    job_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    timezone_name = Column(String(255), nullable=True)
    status = Column(String(255), nullable=False)
    case_no = Column(Integer, ForeignKey('cases.case_no'), nullable=False, index=True)
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
    job_no = Column(Integer, unique=True, nullable=True)
    cancel_details = Column(Text, nullable=True)
    cancel_reason = Column(
        PgEnum(CancelReasonEnum, name="cancel_reason_enum"),
        nullable=True
    )
    computed_status = Column(String(50), nullable=True, default="upcoming")
    actual_session_start_time = Column(DateTime, nullable=True)  
    actual_session_end_time = Column(DateTime, nullable=True)    
    session_duration = Column(String(255), nullable=True)
    session_completed = Column(Boolean, default=False, server_default='false')
    video_upload_deadline = Column(DateTime, nullable=True)
    expected_video_count = Column(Integer, nullable=True)
    mark_is_done_case = Column(Boolean, default=False, server_default='false')
    mark_is_done_witnesses = Column(Boolean, default=False, server_default='false')
    mark_is_done_attorneys = Column(Boolean, default=False, server_default='false')
    mark_is_done_billings = Column(Boolean, default=False, server_default='false')
    mark_is_done_equipment_time = Column(Boolean, default=False, server_default='false')
    

    case = relationship(
        "Cases",
        back_populates="jobs",
        lazy="joined"
    )

    attorneys = relationship(
        "Attorneys",
        back_populates="job",
        cascade="all, delete-orphan"
    )

    billing = relationship(
        "Billings",
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan"
    )

    additional_documents = relationship(
        "AdditionalDocuments",
        back_populates="job",
        cascade="all, delete-orphan"
    )

    equipment_time = relationship(
        "EquipmentTime",
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan"
    )

    witnesses = relationship(
        "Witnesses",
        back_populates="job",
        cascade="all, delete-orphan"
    )

    tasks = relationship(
        "JobsTasks",
        back_populates="job",
        cascade="all, delete-orphan"
    )