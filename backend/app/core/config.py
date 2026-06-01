from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from functools import cached_property


class Settings(BaseSettings):
    # =========================
    # Core API
    # =========================
    PROJECT_NAME: str = "DYLETH API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # =========================
    # Security
    # =========================
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60   # 1h — réduire via .env si besoin
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30    # 30j — renouvelé silencieusement par le client
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30

    # =========================
    # Database
    # =========================
    DB_TYPE: str = "postgresql+asyncpg"
    DB_USER: str = "dyleth"
    DB_PASSWORD: str = "dyleth123"
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 5432
    DB_NAME: str = "dyleth"

    @cached_property
    def DATABASE_URL(self) -> str:
        return (
            f"{self.DB_TYPE}://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # =========================
    # Infra / Services
    # =========================
    REDIS_URL: str = "redis://localhost:6379/0"
    QDRANT_URL: str = "http://localhost:6333"

    # =========================
    # CORS / Frontend
    # =========================
    CORS_ORIGINS: List[str] = ["*"]
    FRONTEND_HOST: str

    # =========================
    # ML / Rate limiting
    # =========================
    ML_MODEL_PATH: str = "/app/models/ml_models"
    FRAUD_CONFIDENCE_THRESHOLD: float = 0.7
    MAX_REQUESTS_PER_MINUTE: int = 100

    # =========================
    # Quotas
    # =========================
    USER_QUOTA: int = 5
    ORGANISATION_QUOTA: int = 100
    ADMIN_QUOTA: int = 0

    # =========================
    # SMTP / Email
    # =========================
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASS: str
    SMTP_SECURE: bool = True
    SMTP_TIMEOUT_SECONDS: int = 30
    SMTP_DEBUG: bool = False

    EMAILS_FROM_NAME: str
    EMAILS_FROM_EMAIL: str

    # =========================
    # Pydantic config (v2)
    # =========================
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="forbid",  # 🔒 strict mode (recommandé prod)
    )


settings = Settings()