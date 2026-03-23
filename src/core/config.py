from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """
    Configuration Class - loads from ENVs/.env.local
    """

    # JWT
    ACCESS_TOKEN_EXPIRATION_TIME: int = 10800 
    REFRESH_TOKEN_EXPIRATION_TIME: int = 604800
    SECRET_KEY: str = "sfiw0ef2_kansls23ml-2jwdnslknddsf"
    ALGORITHM: str = "HS256"
    
    # Application
    APPLICATION_NAME: str = "FAST API"
    APPLICATION_VERSION: str = "0.1.0"
    EMAIL_EXPIRATION_DELTA: int = 0
    
    # Timezone Configuration
    DEFAULT_TIMEZONE_PRODUCTION: str = "America/New_York"
    DEFAULT_TIMEZONE_DEVELOPMENT: str = "Asia/Kolkata" 
    
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
    APP_ENV: str = 'production'
    DEBUG: bool = True
    LOG_LEVEL: str = "info"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    #smtp
    SMTP_EMAIL: str = "devendra.la@cisinlabs.com"
    SMTP_PASSWORD: str = "tqtdlyownbflixge"
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    FRONTEND_URL: str = "http://localhost:3000/"

    # Storage / download URL strategy
    # local: serve files from this API via /uploads
    # s3/cdn: future-ready switch for object storage + CDN URLs
    STORAGE_BACKEND: str = "local"
    CDN_BASE_URL: str = ""
    PUBLIC_API_BASE_URL: str = "http://127.0.0.1:8000"

    # RB9 Database (for data sync)
    RB9_DB_USER: str = "postgres"
    RB9_DB_PASSWORD: str = "admin123"
    RB9_DB_HOST: str = "localhost"
    RB9_DB_PORT: int = 5432
    RB9_DB_NAME: str = "external_db"
    
    # Sync Configuration
    SYNC_DATA_DAYS: int = 1  
    SYNC_INTERVAL_MINUTES: int = 2  
    SYNC_DATA_SOURCE: str = "external_db"
    # Sync timeout for large datasets (50-80k records) - in seconds
    # SYNC_TASK_TIMEOUT_SECONDS: int = 10800  # 3 hours (10800 seconds)
    # SYNC_TASK_SOFT_TIMEOUT_SECONDS: int = 10200  # 2 hours 50 minutes (soft limit)

    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def RB9_DATABASE_URL(self) -> str:
        return f"postgresql://{self.RB9_DB_USER}:{self.RB9_DB_PASSWORD}@{self.RB9_DB_HOST}:{self.RB9_DB_PORT}/{self.RB9_DB_NAME}"


    class Config:
        env_file = "ENVs/.env.local"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore" 


@lru_cache
def get_config_settings():
    return Settings()


config = get_config_settings()
