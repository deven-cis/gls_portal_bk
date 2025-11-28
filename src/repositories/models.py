from sqlalchemy import Column, String, LargeBinary, Boolean, Integer

from src.core.models import Base


class Repositories(Base):
    wit_no=Column(Integer, nullable=False)
    file_name = Column(String(255), nullable=True)
    repository_level = Column(String(255), nullable=True)
    file_name = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    job_no = Column(Integer, nullable=False)
    



