from pydantic_settings import BaseSettings
from functools import lru_cache
class Settings(BaseSettings):
    """
    Configuration Class
    """

    DB_USER: str = "postgres"
    DB_PASSWORD: str = "admin123"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "gls_db"
    ACCESS_TOKEN_EXPIRATION_TIME: int = 0
    REFRESH_TOKEN_EXPIRATION_TIME: int = 0
    SECRET_KEY: str = ""
    ALGORITHM: str = ""
    APPLICATION_NAME: str = "gls_api"
    APPLICATION_VERSION: str = "1.0.0"
    EMAIL_EXPIRATION_DELTA: int = 0

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = "ENVs/.env.local"
        env_file_encoding = "utf-8"


@lru_cache
def get_config_settings():
    return Settings()


config = get_config_settings()