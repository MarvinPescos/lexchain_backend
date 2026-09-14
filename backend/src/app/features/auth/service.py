import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from supabase import AuthApiError, Client

from app.features.users.repository import UserRepository
from app.infrastructure.clients import build_supabase_auth_client, get_supabase_admin
from app.infrastructure.observability.logging_setup import log
from app.shared.errors.exceptions import (
    BadGatewayError,
    BadRequestError,
    UnauthorizedError,
)
from app.shared.utils import _mask_email

from .schemas import (
    MessageResponse,
    SignInRequest,
    SignInResponse,
    SignInUser,
    SignUpRequest,
    SignUpResponse,
)

_RESEND_MESSAGE = (
    "If that address has an unverified account, "
    "a verification email has been sent. Please check your inbox."
)


class AuthService:
    """
    Service responsible for authentication and identity management.

    Handles Supabase auth operations and synchronizes user data with the local database.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = UserRepository(session)
        self.supabase_admin: Client = get_supabase_admin()

    async def sign_up(self, data: SignUpRequest) -> SignUpResponse:
        """
        Register a new user with Supabase and sync to local database.
        Uses a compensating-delete pattern: if the local DB sync fails after
        the Supabase auth user was created, we best-effort delete the
        Supabase user so we don't leave an orphan in auth.users.

        Args:
            data: SignUpRequest containing email, password and name.

        Returns:
            A `SignUpResponse` with the new user's identity and whether they
            still have to confirm their email.

        Raises:
            BadRequestError: If the user already exists or sign-up fails.
            BadGatewayError: If the Supabase connection fails.
        """
        # 1 Create the user in supabase Auth
        try:
            auth_response = await asyncio.to_thread(
                build_supabase_auth_client().auth.sign_up,
                {
                    "email": data.email,
                    "password": data.password,
                },
            )

        except AuthApiError as e:
            log.warning("auth.signup.rejected", email=_mask_email(data.email), error=str(e))
            if "already registered" in str(e).lower():
                raise BadRequestError(
                    "User already registered. Please sign in or request a new verification email."
                ) from e

            raise BadRequestError("Sign up failed. Please check your details and try again.") from e

        except Exception as e:
            log.error(
                "auth.supabase.signup.error",
                email=_mask_email(data.email),
                error=str(e),
                exc_info=True,
            )
            raise BadGatewayError(
                "Sign up is unavailable right now. Please try again later."
            ) from e

        if not auth_response.user:
            raise BadRequestError("Failed to create user")

        # Step 2: Sync to local DB. If this fails, compensate by deleting
        # the Supabase auth user we just created.
        try:
            # Sync user to local database
            local_user = await self.repo.sync_from_supabase(
                supabase_user_id=auth_response.user.id,
                email=data.email,
                f_name=data.f_name,
                l_name=data.l_name,
                is_email_verified=False,
            )

        except Exception as sync_err:
            log.error(
                "auth.signup.local_sync_failed",
                supabase_user_id=auth_response.user.id,
                email=_mask_email(data.email),
                error=str(sync_err),
            )
            await self._compensate_delete_supabase_user(
                auth_response.user.id,
            )
            # Re-raise so the caller sees the real failure.
            raise

        log.info("auth.signup.succeeded", email=_mask_email(data.email))

        requires_confirmation = auth_response.session is None

        return SignUpResponse(
            message=(
                "Account created successfully. Please check your email to verify your account."
                if requires_confirmation
                else "Account created successfully."
            ),
            user_id=local_user.id,
            email=local_user.email,
            requires_email_confirmation=requires_confirmation,
        )

    async def sign_in(self, data: SignInRequest) -> SignInResponse:
        """
        Authenticate a user with Supabase credentials.

        Args:
            data: SignInRequest containing email and password.

        Returns:
            A `SignInResponse` containing the session tokens and the signed-in
            user.

        Raises:
            UnauthorizedError: If credentials are invalid, the email is not
                verified, or the account is deactivated.
            BadGatewayError: If the Supabase connection fails.
        """

        try:
            # Blocking call — see the note in sign_up.
            auth_response = await asyncio.to_thread(
                build_supabase_auth_client().auth.sign_in_with_password,
                {"email": data.email, "password": data.password},
            )
        except AuthApiError as e:
            log.info("auth.signin.rejected", email=_mask_email(data.email), error=str(e))
            raise UnauthorizedError("Invalid credentials") from e
        except Exception as e:
            log.error(
                "auth.supabase.signin.error",
                email=_mask_email(data.email),
                error=str(e),
                exc_info=True,
            )
            raise BadGatewayError(
                "Sign in is unavailable right now. Please try again later."
            ) from e

        supabase_user = auth_response.user

        if not auth_response.session:
            if supabase_user:
                raise UnauthorizedError(
                    "Please verify your email before signing in. Check your inbox for the confirmation link."
                )
            raise UnauthorizedError("Invalid credentials")

        if not supabase_user:
            raise UnauthorizedError("Invalid credentials")

        await self.repo.sync_from_supabase(
            supabase_user_id=supabase_user.id,
            email=supabase_user.email or data.email,
            is_email_verified=supabase_user.email_confirmed_at is not None,
        )

        user = await self.repo.get_by_supabase_id(supabase_user.id)

        if not user:
            log.error(
                "auth.signin.local_user_missing",
                supabase_user_id=supabase_user.id,
                email=_mask_email(data.email),
            )
            raise UnauthorizedError("Account is not provisioned. Please try again.")

        if not user.is_active:
            log.warning(
                "auth.signin.rejected.inactive_account",
                email=_mask_email(data.email),
            )
            raise UnauthorizedError("Account is deactivated. Contact your administrator.")

        log.info("auth.signin.succeeded", email=_mask_email(data.email))

        return SignInResponse(
            access_token=auth_response.session.access_token,
            refresh_token=auth_response.session.refresh_token,
            expires_in=auth_response.session.expires_in,
            user=SignInUser(
                id=user.id,
                email=user.email,
                role=user.role,
            ),
        )

    async def sign_out(self, access_token: str, user_id: uuid.UUID) -> MessageResponse:
        """
        Revoke the caller's Supabase session.

        Only the refresh token is actually revoked. Access tokens are verified
        locally against the JWKS (see `verify_jwt_token`) and never checked
        against GoTrue, so the token in the caller's hand keeps working until it
        expires — shorten the Supabase access-token TTL if that window matters.
        Clients must discard their copy regardless of what this returns.

        Args:
            access_token: The bearer token presented on this request.
            user_id: The local user id, for logging.

        Returns:
            A `MessageResponse` confirming the session was revoked.

        Raises:
            BadGatewayError: If Supabase is unreachable, in which case the
                refresh token may still be live.
        """
        try:
            # Blocking call — see the note in sign_up.

            await asyncio.to_thread(self.supabase_admin.auth.admin.sign_out, access_token, "global")
        except AuthApiError as e:
            log.info("auth.signout.already_invalid", user_id=user_id, error=str(e))
        except Exception as e:
            log.error(
                "auth.supabase.signout.error",
                user_id=user_id,
                error=str(e),
                exc_info=True,
            )
            raise BadGatewayError(
                "Sign out is unavailable right now. Please try again later."
            ) from e

        log.info("auth.signout.succeeded", user_id=user_id)
        return MessageResponse(message="Signed out successfully.")

    async def resend_verification_email(self, email: str) -> MessageResponse:
        """
        Resend the verification email for an unverified user.

        Args:
            email: The email address to send the verification to.

        Returns:
            A `MessageResponse` carrying a neutral message. The same message is
            returned whether or not the address has an unverified account.
        """

        try:
            await asyncio.to_thread(
                build_supabase_auth_client().auth.resend,
                {"type": "signup", "email": email},
            )
            log.info("auth.verification.resent", email=_mask_email(email))
        except AuthApiError as e:
            log.warning("auth.resend.failed", email=_mask_email(email), error=str(e))
        except Exception as e:  # noqa: BLE001
            log.error(
                "auth.supabase.resend.error",
                email=_mask_email(email),
                error=str(e),
                exc_info=True,
            )

        return MessageResponse(message=_RESEND_MESSAGE)

    async def _compensate_delete_supabase_user(self, supabase_user_id: str) -> None:
        """
        Best-effor deletion of a Supabase auth user after a failed local sync.


        This is intentionally swallow-all: the caller is already about to
        re-raise the original error, and we don't want cleanup failures to
        mask it. We do log loudly so orphans can be found and reconciled
        later (e.g. when the outbox pattern is introduced).
        """

        try:
            # Blocking call — see the note in sign_up.
            await asyncio.to_thread(self.supabase_admin.auth.admin.delete_user, supabase_user_id)
            log.warning(
                "auth.signup.compensation.deleted_supabase_user",
                supabase_user_id=supabase_user_id,
            )

        except Exception as clean_up_err:  # noqa: BLE001
            log.error(
                "auth.signup.compensation.failed",
                supabase_user_id=supabase_user_id,
                error=str(clean_up_err),
                exc_info=True,
            )
