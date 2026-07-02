from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Student Complaint Management System"
    ENV: str = "dev"
    DEBUG: bool = True
    PORT: int = 8000

    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    AWS_S3_BUCKET_NAME: str = "student-complaint-attachments"
    AWS_ACCESS_KEY_ID: str = "mock-aws-key-id"
    AWS_SECRET_ACCESS_KEY: str = "mock-aws-secret-key"
    AWS_REGION: str = "us-east-1"

    RATE_LIMIT_PER_MINUTE: int = 100
    CACHING_ENABLED: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()  # type: ignore[call-arg]
