from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.core.config import config

DATABASE_URL = config.DATABASE_URL

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine, autoflush=False)

Base = declarative_base()

# Create a session instance
db = SessionLocal()

def get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()