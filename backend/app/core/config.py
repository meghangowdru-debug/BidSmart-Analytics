"""
BidSmart Analytics — Application Configuration Module
Uses Pydantic BaseSettings to load and validate environment variables.
"""

import ipaddress
from typing import List, Union
from urllib.parse import quote_plus
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json
import os


PLACEHOLDER_SECRET_VALUES = {
    "default-insecure-secret-key-change-in-production",
    "development-secret-key-change-me",
    "replace-this-with-a-secure-random-secret-key-in-production",
    "change-me",
    "change-me-in-local-dev",
}

PLACEHOLDER_DB_PASSWORD_VALUES = {
    "bidsmart_pass123",
    "replace_with_your_mysql_password",
    "change-me",
    "change-me-in-local-dev",
    "password",
    "mysql_password",
}


def _is_local_database_host(host: str) -> bool:
    normalized = host.strip().lower().rstrip(".")
    if normalized in {"localhost", "localhost.localdomain"} or normalized.endswith(
        ".localhost"
    ):
        return True
    try:
        address = ipaddress.ip_address(normalized.strip("[]"))
    except ValueError:
        return False
    return address.is_loopback or address.is_unspecified


class Settings(BaseSettings):
    # Project Info
    PROJECT_NAME: str = "BidSmart Analytics API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Security & Tokens
    SECRET_KEY: str = "development-secret-key-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database Configuration
    MYSQL_SERVER: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "bidsmart_user"
    MYSQL_PASSWORD: str = "change-me-in-local-dev"
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

    # Payment processing is restricted to Razorpay test mode.
    RAZORPAY_MODE: str = "test"
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    RAZORPAY_CURRENCY: str = "USD"

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
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return parsed
                except Exception:
                    pass
            values = [i.strip() for i in v.split(",") if i.strip()]
            return values
        elif isinstance(v, list):
            return v
        return []

    @field_validator("BACKEND_CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, v: List[str]) -> List[str]:
        normalized = []
        for origin in v:
            value = str(origin).strip()
            if not value:
                continue
            if "*" in value:
                raise ValueError("Wildcard CORS origins are not allowed. Configure explicit origins only.")
            normalized.append(value)
        return normalized

    @field_validator("RAZORPAY_MODE", mode="before")
    @classmethod
    def validate_razorpay_mode(cls, value: str) -> str:
        if isinstance(value, str) and value.strip().lower() == "test":
            return "test"
        raise ValueError("Razorpay is restricted to TEST mode.")

    @field_validator("RAZORPAY_CURRENCY", mode="before")
    @classmethod
    def validate_razorpay_currency(cls, value: str) -> str:
        if isinstance(value, str) and value.strip().upper() == "USD":
            return "USD"
        raise ValueError("Razorpay payment currency must remain USD to match marketplace amounts.")

    @model_validator(mode="after")
    def validate_security_defaults(self):
        env_name = (self.ENVIRONMENT or "").strip().lower()
        is_production = env_name in {"production", "prod"}
        is_render_deployment = os.getenv("RENDER", "").strip().lower() in {
            "true",
            "1",
        }

        if is_render_deployment and not is_production:
            raise ValueError(
                "ENVIRONMENT must be explicitly set to production for Render deployments."
            )

        if is_production and self.DEBUG:
            raise ValueError("DEBUG must be False in production mode.")

        if is_production and (
            not self.SECRET_KEY
            or self.SECRET_KEY in PLACEHOLDER_SECRET_VALUES
            or len(self.SECRET_KEY) < 32
        ):
            raise ValueError("SECRET_KEY must be provided as a strong random value in production mode.")

        if is_production and (
            not self.MYSQL_PASSWORD
            or self.MYSQL_PASSWORD in PLACEHOLDER_DB_PASSWORD_VALUES
        ):
            raise ValueError("MYSQL_PASSWORD must be configured explicitly in production mode.")

        if is_production and (
            not self.MYSQL_SERVER.strip()
            or _is_local_database_host(self.MYSQL_SERVER)
            or not self.MYSQL_USER.strip()
            or not self.MYSQL_DB.strip()
        ):
            raise ValueError(
                "Production MySQL server, user, and database must be configured "
                "with a non-loopback database server."
            )

        return self

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Construct the MySQL connection URI."""
        encoded_user = quote_plus(self.MYSQL_USER)
        encoded_password = quote_plus(self.MYSQL_PASSWORD)

        return (
            f"mysql+pymysql://{encoded_user}:{encoded_password}@"
            f"{self.MYSQL_SERVER}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
            "?charset=utf8mb4"
        )


settings = Settings()
