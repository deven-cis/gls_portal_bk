from sqlalchemy import Column, String, LargeBinary, Boolean, Integer
from sqlalchemy.orm import relationship
from src.core.models import Base

class Users(Base):
    user_no = Column(Integer, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    middle_name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    login_name = Column(String, unique=True, index=True, nullable=True)
    login_password = Column(LargeBinary)
    require_password_change = Column(Boolean, default=False)
    profile_image_url = Column(String, nullable=True)
    person_no = Column(Integer, unique=True, nullable=True, index=True)
    is_active = Column(Boolean, default=True, server_default='true')

    # Jobs assigned TO this user (as assignee)
    assigned_jobs = relationship(
        "JobAssignment",
        foreign_keys="[JobAssignment.assignee_id]",
        back_populates="assignee"
    )
    
    # Jobs assigned BY this user (as assigner)
    jobs_assigned_by_me = relationship(
        "JobAssignment",
        foreign_keys="[JobAssignment.assigner_id]",
        back_populates="assigner"
    )