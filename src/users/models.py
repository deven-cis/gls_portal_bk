from sqlalchemy import Column, String, LargeBinary, Boolean

from src.core.models import Base


class Users(Base):
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    login_name = Column(String, unique=True, index=True, nullable=False) # Fix the missing import
    login_password = Column(LargeBinary)
    require_password_change = Column(Boolean, default=False)
    profile_image_url = Column(String, nullable=True)