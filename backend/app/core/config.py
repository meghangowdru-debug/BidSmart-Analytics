"""
BidSmart Analytics — Application Configuration Module
Uses Pydantic BaseSettings to load and validate environment variables.
"""

from typing import List, Union
from urllib.parse import quote_plus
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json
import os


class Settings(BaseSettings):
    # Project Info
    PROJECT_NAME: str = "BidSmart Analytics API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Security & Tokens
    SECRET_KEY: str = "default-insecure-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database Configuration
    MYSQL_SERVER: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "bidsmart_user"
    MYSQL_PASSWORD: str = "bidsmart_pass123"
    MYSQL_DB: str = "bidsmart_db"

    # SQLAlchemy Pool Configuration
    MYSQL_POOL_SIZE: int = 20
    MYSQL_MAX_OVERFLOW: int = 10
    MYSQL_POOL_TIMEOUT: int = 30
    MYSQL_POOL_RECYCLE: int = 1800
    MYSQL_ECHO: bool = False

    # Background Auction Scheduler
    ENABLE_AUCTION_SCHEDULER: bool = True
    SCHEDULER_INTERVAL_SECONDS: int = 30

    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    # AI Configuration (Optional)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """
        Dynamically construct MySQL connection URI for PyMySQL.
        Uses quote_plus on credentials to handle special characters (@, #, :, /, etc.) safely.
        """
        encoded_user = quote_plus(self.MYSQL_USER)
        encoded_password = quote_plus(self.MYSQL_PASSWORD)
        return (
            f"mysql+pymysql://{encoded_user}:{encoded_password}@"
            f"{self.MYSQL_SERVER}:{self.MYSQL_PORT}/{self.MYSQL_DB}?charset=utf8mb4"
        )


settings = Settings()
