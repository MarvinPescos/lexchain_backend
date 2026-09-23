from typing import Annotated

from fastapi import Depends

from app.infrastructure.database import DbSession

from .service import AuthService


def get_auth_service(db: DbSession) -> AuthService:
    """Dependency injection (provides AuthService with database session)"""
    return AuthService(db)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
