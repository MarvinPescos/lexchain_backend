import uuid

from pydantic import BaseModel, EmailStr, Field

from app.shared.utils.validators import ValidatedName, ValidatedPassword


class SignUpRequest(BaseModel):
    email: EmailStr = Field(..., description="Valid email for this user")
    password: ValidatedPassword = Field(..., description="Valid Password")
    f_name: ValidatedName = Field(..., description="Valid first name")
    l_name: ValidatedName = Field(..., description="Valid last name")


class SignUpResponse(BaseModel):
    message: str = Field(..., description="Message containing what to do next.")
    user_id: uuid.UUID = Field(..., description="Contains the user id the response")
    email: EmailStr = Field(..., description="Email of this user/response")
    requires_email_confirmation: bool = Field(
        ..., description="session will be None until the user verifies their email"
    )


class SignInRequest(BaseModel):
    email: EmailStr = Field(..., description="Valid email for this user")
    password: str = Field(..., description="The user's password")


class SignInUser(BaseModel):
    """The signed-in user, as the client needs it."""

    id: uuid.UUID = Field(..., description="Local database user ID")
    email: EmailStr = Field(..., description="User's email address")
    role: str = Field(
        ...,
        description=(
            "lawyer — full authority (upload, review, finalize, admin panel); "
            "user — client, may only view documents they are a party to."
        ),
    )


class SignInResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token for API authentication")
    refresh_token: str = Field(..., description="Token used to obtain a new access token")
    token_type: str = Field(default="bearer", description="Token type, always 'bearer'")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: SignInUser = Field(..., description="The signed-in user")


class ResendVerificationRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address to resend verification to")


class MessageResponse(BaseModel):
    message: str = Field(..., description="Response message")
