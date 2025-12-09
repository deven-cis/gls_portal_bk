from sqlalchemy import Column, DateTime, Time, Integer, String, BigInteger, ForeignKey
from sqlalchemy.types import Text
from sqlalchemy.orm import relationship
from src.core.models import Base
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
import enum
from src.attorneys.models import Attorneys
from src.billings.models import Billings
from src.additional_documents.models import AdditionalDocuments
from src.equipment_time.models import EquipmentTime
from src.witnesses.models import Witnesses
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
    # Using string reference to avoid circular imports
    case = relationship(
        "src.cases.models.Cases",
        back_populates="jobs",
        lazy="joined",
    )
    
    # One-to-many: each job can have multiple attorneys
    # Using string reference to avoid circular imports
    attorneys = relationship(
        Attorneys,
        back_populates="job",
        cascade="all, delete-orphan"
    )
    
    # One-to-one relationship with Billings
    # Using string reference to avoid circular imports
    billing = relationship(
        Billings,
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    # One-to-many relationship with AdditionalDocuments
    # Using string reference to avoid circular imports
    additional_documents = relationship(
        AdditionalDocuments,
        back_populates="job",
        cascade="all, delete-orphan"
    )
    
    # One-to-one relationship with EquipmentTime
    # Using string reference to avoid circular imports
    equipment_time = relationship(
        EquipmentTime,
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    # One-to-many relationship with Witnesses
    # Using string reference to avoid circular imports
    witnesses = relationship(
        Witnesses,
        back_populates="job",
        cascade="all, delete-orphan"
    )
    