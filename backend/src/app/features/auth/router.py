from fastapi import APIRouter, Request, Response, status

from app.core import settings
from app.infrastructure.rate_limiting import limiter
from app.infrastructure.security.dependencies import CurrentUser, TokenCredentials

from .dependencies import AuthServiceDep
from .schemas import (
    MessageResponse,
    ResendVerificationRequest,
    SignInRequest,
    SignInResponse,
    SignUpRequest,
    SignUpResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Every route below takes `request` and `response` purely for slowapi. It reads
# the caller's IP off `request` (and refuses to wrap a handler without one), and
# writes the X-RateLimit-* headers into `response` — a route returning a pydantic
# model has no Response of its own, and slowapi raises rather than skipping when
# that parameter is missing, which turns every success into a 500.


@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="""
    Create a new user account with email, password, and name.

    - **Email Verification**: If enabled in Supabase, user must verify email before signing in.
    - **Name**: First and last name, 1-50 characters, letters/spaces/hyphens/apostrophes.
    - **Password**: Must be at least 8 characters with uppercase, lowercase, and digit.
    """,
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Invalid input or user already exists"},
        429: {"description": "Too many signups from this IP"},
        502: {"description": "Failed to connect to Supabase"},
    },
)
@limiter.limit(settings.RATE_LIMIT_SIGNUP)
async def sign_up(
    request: Request,
    response: Response,
    data: SignUpRequest,
    service: AuthServiceDep,
) -> SignUpResponse:
    return await service.sign_up(data)


@router.post(
    "/signin",
    summary="Sign in a user",
    description="""
    Authenticate a user with email and password.

    - **Returns**: Access token, refresh token, and token expiration time.
    - **Email Verification**: User must have verified their email to sign in.
    """,
    responses={
        200: {"description": "Successfully authenticated"},
        401: {"description": "Invalid credentials, email not verified, or account deactivated"},
        429: {"description": "Too many sign-in attempts from this IP"},
        502: {"description": "Failed to connect to Supabase"},
    },
)
@limiter.limit(settings.RATE_LIMIT_SIGNIN)
async def sign_in(
    request: Request,
    response: Response,
    data: SignInRequest,
    service: AuthServiceDep,
) -> SignInResponse:
    return await service.sign_in(data)


@router.post(
    "/logout",
    summary="Sign out the current user",
    description="""
    Revoke the current user's Supabase session.

    - **Refresh token**: revoked, so the session cannot be renewed.
    - **Access token**: stays valid until it expires. Tokens are verified
      locally, not against Supabase, so there is no way to cancel one early.
      Clients must discard their copy.
    - **Scope**: signs the account out of every device, not just this one.
    - **Idempotent**: signing out an already-ended session still succeeds.
    """,
    responses={
        200: {"description": "Session revoked"},
        401: {"description": "Missing, invalid, or expired token"},
        429: {"description": "Too many logout calls from this IP"},
        502: {"description": "Failed to connect to Supabase"},
    },
)
@limiter.limit(settings.RATE_LIMIT_LOGOUT)
async def logout(
    request: Request,
    response: Response,
    user: CurrentUser,
    credentials: TokenCredentials,
    service: AuthServiceDep,
) -> MessageResponse:
    return await service.sign_out(credentials.credentials, user.user_id)


@router.post(
    "/resend-verification",
    summary="Resend verification email",
    description="""
    Resend the verification email for users who haven't verified their email yet.

    - **Use Case**: When verification link expires or email was not received.
    - **Response**: Always the same message, whether or not the address has an account.
    """,
    responses={
        200: {"description": "Request accepted"},
        429: {"description": "Too many verification emails requested from this IP"},
    },
)
@limiter.limit(settings.RATE_LIMIT_RESEND_VERIFICATION)
async def resend_verification(
    request: Request,
    response: Response,
    data: ResendVerificationRequest,
    service: AuthServiceDep,
) -> MessageResponse:
    return await service.resend_verification_email(data.email)
