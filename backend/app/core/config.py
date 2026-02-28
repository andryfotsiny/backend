from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    PROJECT_NAME: str = "DYLETH API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str

    # Redis & Qdrant
    REDIS_URL: str = "redis://localhost:6379/0"
    QDRANT_URL: str = "http://localhost:6333"

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # ML Configuration
    ML_MODEL_PATH: str = "/app/models/ml_models"
    FRAUD_CONFIDENCE_THRESHOLD: float = 0.7

    # Rate limiting
    MAX_REQUESTS_PER_MINUTE: int = 100

    USER_QUOTA: int = 5
    ORGANISATION_QUOTA: int = 100
    ADMIN_QUOTA: int = 0

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
