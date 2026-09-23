import asyncio
import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from app.infrastructure.database import DbSession
from app.infrastructure.observability.logging_setup import log
from app.shared.constants import ROLE_LAWYER
from app.shared.errors.exceptions import ForbiddenError, UnauthorizedError

from .jwt_handler import verify_jwt_token

# Security scheme for swagger
security_scheme = HTTPBearer(
    scheme_name="Bearer Token", description="Enter your Supabase JWT token"
)

TokenCredentials = Annotated[HTTPAuthorizationCredentials, Depends(security_scheme)]


# Schema for authenticated user!
class AuthenticatedUser(BaseModel):
    """
    Represents an authenticated user in the system
    Domain model (not an API scheme)
    """

    user_id: uuid.UUID = Field(..., description="Local database user ID")
    email: str | None = Field(..., description="User email")
    is_active: bool = Field(..., description="Status of account")
    role: str = Field(..., description="User role (from users.role)")

    def is_lawyer(self) -> bool:
        """Check if user holds lawyer authority.

        There is no separate admin tier: the lawyer is the primary authority
        and also runs the admin panel.
        """
        return self.role == ROLE_LAWYER

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "email": "user@example.com",
                "is_active": True,
                "role": "user",
            }
        },
    )


async def get_current_user(
    credentials: TokenCredentials,
    session: DbSession,
) -> AuthenticatedUser:
    """
    FastApi dependecy: get user from token and ensure they exist in db
    """

    token = credentials.credentials
    payload = await asyncio.to_thread(verify_jwt_token, token)

    from app.features.accounts.repository import UserRepository

    user_repo = UserRepository(session)
    supabase_user_id = payload["sub"]

    user_db = await user_repo.get_by_supabase_id(supabase_user_id)
    if not user_db:
        log.warning(
            "auth.rejected.unprovisioned_user",
            supabase_user_id=supabase_user_id,
        )
        raise UnauthorizedError("Account is not provisioned. Please sign in again.")

    role = user_db.role

    if not user_db.is_active:
        log.warning(
            "auth.rejected.inactive_account",
            user_id=user_db.id,
            supabase_user_id=supabase_user_id,
        )
        raise ForbiddenError("Account is deactivated. Contact your administrator.")

    log.debug(f"Authenticated user: {user_db.id}")

    return AuthenticatedUser(
        user_id=user_db.id,
        # The stored email is now the source of truth — nothing on this path
        # writes the JWT claim back, so reading it here would let the two
        # disagree silently.
        email=user_db.email,
        is_active=user_db.is_active,
        role=role,
    )


# Annotate route parameters with these aliases — `user: CurrentUser` — rather than
# defaulting them to a `Depends()` call.
CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]


def require_auth(
    user: CurrentUser,
) -> AuthenticatedUser:
    """Simplified Dependency alias for requiring authentication"""
    return user


def require_lawyer(
    user: CurrentUser,
) -> AuthenticatedUser:
    """Require lawyer authority — the only privileged role"""
    if not user.is_lawyer():
        raise ForbiddenError("Only lawyer can perform this action")
    return user


LawyerUser = Annotated[AuthenticatedUser, Depends(require_lawyer)]
