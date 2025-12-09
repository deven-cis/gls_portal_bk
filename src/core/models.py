from datetime import datetime

from sqlalchemy import Column, Integer, DateTime,Boolean
from sqlalchemy.ext.declarative import as_declarative
from sqlalchemy.orm import declared_attr

from src.core.database import get_db
from src.core.context import get_context, get_context_db


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
        """
        Returns the Queryset Object of class
        """
        db = cls.get_session()
        return db.query(cls)

    @classmethod
    def get_session(cls):
        """
        Return Current Database session
        """
        return get_context_db() or next(get_db())

    @classmethod
    def save(cls, instance):
        """
        Save the instance on the database - Update or Create a new record
        """
        db = cls.get_session()
        instance.last_modified_at = datetime.now()
        
        # Get entered_by from context (should be integer)
        entered_by = get_context('entered_by')
        if entered_by is None:
            # Fallback if context is not set (should not happen in normal flow)
            entered_by = 0  # or raise an error if context is required
        
        instance.last_modified_by = entered_by
        
        if not instance.id:
            instance.entered_at = datetime.now()
            instance.entered_by = entered_by
            db.add(instance)

        db.commit()
        db.refresh(instance)
        return instance

    @classmethod
    def get(cls, id: int):
        """
        Fetch the record by id
        """
        return cls.get_queryset().filter(cls.id == id).first()

    @classmethod
    def fetch_records(
        cls,
        filters: dict = {},
    ):
        """
        Fetch the records by appling respective filters
        """
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
        """
        Check for specific records exists or not
        """
        if filters:
            records = cls.fetch_records(filters)
            if records:
                return True
            return False
        return None