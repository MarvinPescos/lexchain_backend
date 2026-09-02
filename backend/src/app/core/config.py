from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    # Database Configuration
    DB_USER: str = Field(..., description="Database Username")
    DB_PASS: str = Field(..., min_length=1, description="Database password")
    DB_HOST: str = Field(..., description="Database host")
    DB_PORT: int = Field(..., ge=1, le=65535, description="Database port")
    DB_NAME: str = Field(..., min_length=1, description="Database name")

    ENVIRONMENT: str = Field(..., description="development or production")

    DB_URL: str = Field(..., description="Database URL")
    TEST_DB_URL: str = Field(..., description="Database URL for testing")

    # Connection pool tuning. Defaults match SQLAlchemy's own, except
    # DB_POOL_RECYCLE, which guards against managed Postgres / pgbouncer
    # dropping idle connections. Override per environment as needed.
    DB_ECHO: bool = Field(default=False, description="Log every emitted SQL statement")
    DB_POOL_PRE_PING: bool = Field(
        default=True, description="Test connections for liveness before checkout"
    )
    DB_POOL_SIZE: int = Field(default=5, ge=1, description="Connections kept open in the pool")
    DB_MAX_OVERFLOW: int = Field(
        default=10, ge=0, description="Connections allowed beyond DB_POOL_SIZE under load"
    )
    DB_POOL_RECYCLE: int = Field(
        default=1800, description="Seconds before a connection is recycled; -1 disables"
    )


settings = Settings()  # pyright: ignore[reportCallIssue]
