from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core import settings
from app.infrastructure.observability.logging_setup import log

from .exceptions import DatabaseConnectionError

async_engine: AsyncEngine = create_async_engine(
    settings.DB_URL,
    echo=settings.DB_ECHO,
    pool_pre_ping=settings.DB_POOL_PRE_PING,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE,
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides a database session.
    Automatically handles commitr/rollback and cleanup
    """

    async with AsyncSessionLocal() as session:
        try:
            log.debug("Database session created")
            yield session
            await session.commit()
        except SQLAlchemyError as e:
            await session.rollback()
            log.error("Database error: ", exc_info=True)
            raise DatabaseConnectionError(f"Database operation failed: {e!s}", original_error=e)
        except Exception as e:
            await session.rollback()
            log.error(f"Unexpected error: {e!s}", exc_info=True)
            raise
        finally:
            await session.close()


# Declare the dependency once here so call sites annotate `session: DbSession`
# instead of putting a `Depends()` call in an argument default.
DbSession = Annotated[AsyncSession, Depends(get_db)]


async def close_db():
    """
    Close database connections.
    Call this on application shutdown.
    """
    await async_engine.dispose()
    log.info("Database connection closed")
