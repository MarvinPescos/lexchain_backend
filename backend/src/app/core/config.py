from limits import parse_many
from pydantic import Field, field_validator
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
    # TEST_DB_URL: str = Field(..., description="Database URL for testing")

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

    SUPABASE_URL: str = Field(..., description="Supabase project URL")
    SUPABASE_ANON_KEY: str = Field(..., description="Supabase anonymous key")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(
        ..., description="Supabase role key for admin operations"
    )

    # Rate limiting. Every value is a slowapi limit string ("<count>/<period>")
    # counted per client IP. The unauthenticated auth routes get the tight
    # limits; RATE_LIMIT_DEFAULT is the ceiling every other route falls back to.
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Master switch for IP rate limiting")
    RATE_LIMIT_DEFAULT: str = Field(
        default="100/minute", description="Fallback limit for routes without their own"
    )
    RATE_LIMIT_SIGNUP: str = Field(default="5/hour", description="Limit for POST /auth/signup")
    RATE_LIMIT_SIGNIN: str = Field(default="5/minute", description="Limit for POST /auth/signin")
    RATE_LIMIT_LOGOUT: str = Field(default="20/minute", description="Limit for POST /auth/logout")
    RATE_LIMIT_RESEND_VERIFICATION: str = Field(
        default="3/hour", description="Limit for POST /auth/resend-verification"
    )

    @field_validator(
        "RATE_LIMIT_DEFAULT",
        "RATE_LIMIT_SIGNUP",
        "RATE_LIMIT_SIGNIN",
        "RATE_LIMIT_LOGOUT",
        "RATE_LIMIT_RESEND_VERIFICATION",
    )
    @classmethod
    def _validate_rate_limit(cls, value: str) -> str:
        """Reject limit strings slowapi cannot parse.

        slowapi only *logs* a parse failure and then leaves the route
        unlimited, so a typo like "5/min" would silently turn the limit off.
        Failing at startup makes that a loud error instead of a quiet hole.

        Args:
            value: The candidate limit string.

        Returns:
            The value unchanged, once it is known to parse.

        Raises:
            ValueError: If the string is not a valid rate limit expression.
        """
        try:
            parse_many(value)
        except ValueError as exc:
            raise ValueError(f"Invalid rate limit string: {value!r}") from exc
        return value


settings = Settings()  # pyright: ignore[reportCallIssue]
