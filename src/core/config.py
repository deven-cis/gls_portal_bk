from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """
    Configuration Class - loads from ENVs/.env.local
    """

    # JWT
    ACCESS_TOKEN_EXPIRATION_TIME: int = 10,800  # 2 minutes for testing (change back to 6600 for production)
    REFRESH_TOKEN_EXPIRATION_TIME: int = 604800
    SECRET_KEY: str = "sfiw0ef2_kansls23ml-2jwdnslknddsf"
    ALGORITHM: str = "HS256"
    
    # Application
    APPLICATION_NAME: str = "FAST API"
    APPLICATION_VERSION: str = "0.1.0"
    EMAIL_EXPIRATION_DELTA: int = 0
    
    # Database
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "admin123"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "new_gls_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # FastAPI
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "info"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    #smtp
    SMTP_EMAIL: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_SERVER: str = ""
    SMTP_PORT: int = 0
    FRONTEND_URL: str = "http://localhost:3000/"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = "ENVs/.env.local"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields like DATABASE_URL from .env.local


@lru_cache
def get_config_settings():
    return Settings()


config = get_config_settings()