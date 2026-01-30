from datetime import datetime

from sqlalchemy import Column, Integer, DateTime,Boolean
from sqlalchemy.ext.declarative import as_declarative
from sqlalchemy.orm import declared_attr
from src.core.database import get_db
from src.core.context import get_context, get_context_db
from src.core.logger import logger

@as_declarative()
class Base:

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True, index=True)
    entered_at = Column(DateTime, default=datetime.utcnow)
    entered_by = Column(Integer, nullable=False)
    last_modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_modified_by = Column(Integer, nullable=False)
    is_archived = Column(Boolean, default=False, server_default='false')

    @classmethod
    def get_queryset(cls):
        try:
            db = cls.get_session()
            return db.query(cls)
        except Exception as e:
            logger.error(f"Error getting queryset: {str(e)}")
            return None

    @classmethod
    def get_session(cls):
        try:
            return get_context_db() or next(get_db())
        except Exception as e:
            logger.error(f"Error getting session: {str(e)}")
            return None

    def save(self):  
        try:
            db = self.get_session()
            self.last_modified_at = datetime.now()
            
            entered_by = get_context('entered_by')
            if entered_by is None:
                entered_by = 0

            self.last_modified_by = entered_by
            if not self.id:
                self.entered_at = datetime.now()
                self.entered_by = entered_by
                db.add(self)
            db.commit()
            db.refresh(self)
            return self
        except Exception as e:
            logger.error(f"Error saving: {str(e)}")
            return None

    @classmethod
    def get(cls, id: int):
        query = cls.get_queryset()
        return query.filter(cls.id == id).first()

    @classmethod
    def fetch_records(
        cls,
        filters: dict = {},
    ):
        query = cls.get_queryset()
        if filters:
            for key, value in filters.items():
                if hasattr(cls, key):
                    column = getattr(cls, key)
                    if isinstance(value, (list, tuple, set)):
                        query = query.filter(column._in(value))
                    elif isinstance(value, str):
                        query = query.filter(column.ilike(f"%{value}%"))
                    else:
                        query = query.filter(column == value)

        return query.all()

    @classmethod
    def check_exist(cls, filters: dict = {}):
        try:
            if filters:
                records = cls.fetch_records(filters)
                if records:
                    return True
                else:
                    return False    
            else:
                return False
        except Exception as e:
            logger.error(f"Error checking exist(check_exist): {str(e)}")
            return False