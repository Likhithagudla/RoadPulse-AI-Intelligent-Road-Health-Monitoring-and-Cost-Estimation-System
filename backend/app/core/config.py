"""
RoadPulse AI - Core Application Configuration
Loads and validates environment variables using pydantic-settings.
Enforces secure defaults, prevents secret leakage, and dynamically resolves paths.
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directories
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
ENV_FILE = BACKEND_DIR / ".env"

logger = logging.getLogger("roadpulse.config")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "RoadPulse AI Assessment System"
    VERSION: str = "2.1.0"
    API_V1_STR: str = "/api"

    # Security
    SECRET_KEY: str = Field(
        default="roadpulse_dev_fallback_secret_key_needs_override_in_production_8f3a",
        description="JWT cryptographic signing secret",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # Password Policy
    MIN_PASSWORD_LENGTH: int = 8
    REQUIRE_PASSWORD_COMPLEXITY: bool = True

    # Database
    DATABASE_URL: str = Field(
        default=f"sqlite:///{BACKEND_DIR / 'road_ai.db'}",
        description="Database connection string",
    )

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    ALLOWED_ORIGINS: Union[str, List[str]] = "*"

    # Rate Limiting
    AUTH_RATE_LIMIT_MAX_ATTEMPTS: int = 5
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Regional Engineering Cost
    DEFAULT_SOR_REGION: str = "Default"

    # Storage Paths
    UPLOAD_DIR: str = str(PROJECT_ROOT / "uploads")
    DASHBOARD_DIR: str = str(PROJECT_ROOT / "dashboard")
    AI_MODELS_DIR: str = str(PROJECT_ROOT / "ai_models")

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        if isinstance(v, str) and v.startswith("sqlite:///") and not v.startswith("sqlite:////"):
            # Check if it has a Windows drive letter e.g. sqlite:///C:/
            after_prefix = v[len("sqlite:///"):]
            if len(after_prefix) >= 2 and after_prefix[1] == ":":
                return v
            # Relative sqlite path: resolve relative to PROJECT_ROOT
            clean_rel = after_prefix.lstrip("./\\")
            resolved = (PROJECT_ROOT / clean_rel).resolve()
            return f"sqlite:///{resolved.as_posix()}"
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 16:
            raise ValueError("SECRET_KEY must be at least 16 characters long.")
        if "default" in v.lower() or "secret" in v.lower():
            if os.getenv("ENVIRONMENT") == "production":
                raise ValueError("Insecure default SECRET_KEY detected in production environment.")
        return v

    @property
    def cors_origins(self) -> List[str]:
        if isinstance(self.ALLOWED_ORIGINS, list):
            return self.ALLOWED_ORIGINS
        if self.ALLOWED_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def upload_path(self) -> Path:
        p = Path(self.UPLOAD_DIR)
        if not p.is_absolute():
            p = (BACKEND_DIR / p).resolve()
        p.mkdir(parents=True, exist_ok=True)
        (p / "images").mkdir(parents=True, exist_ok=True)
        (p / "videos").mkdir(parents=True, exist_ok=True)
        (p / "annotated").mkdir(parents=True, exist_ok=True)
        return p

    @property
    def dashboard_path(self) -> Path:
        p = Path(self.DASHBOARD_DIR)
        if not p.is_absolute():
            p = (BACKEND_DIR / p).resolve()
        return p


settings = Settings()
