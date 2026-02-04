"""API Configuration settings for production and development"""

import os
from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache
from typing import Optional, Union


class APISettings(BaseSettings):
    """API-specific settings loaded from environment"""

    # App info
    app_name: str = "ResumeAI"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    log_level: str = "info"

    # CORS settings - can be comma-separated string or list
    cors_origins: Union[str, list[str]] = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # RAG settings
    default_backend: str = "groq"
    chroma_persist_dir: str = "./data/chroma"

    # Rate limiting
    rate_limit_per_minute: int = 60

    # API Keys (optional - loaded from env)
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    def get_cors_origins(self) -> list[str]:
        """Get CORS origins, parsing from env if needed"""
        # Check if CORS_ORIGINS is set as env var (comma-separated)
        env_origins = os.getenv("CORS_ORIGINS")
        if env_origins:
            return [o.strip() for o in env_origins.split(",") if o.strip()]
        return self.cors_origins


@lru_cache
def get_settings() -> APISettings:
    """Get cached settings instance"""
    return APISettings()
