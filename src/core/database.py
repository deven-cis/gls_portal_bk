from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.core.config import config

DATABASE_URL = config.DATABASE_URL

engine = create_engine(DATABASE_URL, pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()

# Create a session instance
# db = SessionLocal()

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()