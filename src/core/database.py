from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.core.config import config

DATABASE_URL = config.DATABASE_URL

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine, autoflush=False)



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()