from typing import Annotated

import phonenumbers
from pydantic import AfterValidator

# Characters allowed inside a name, on top of Unicode letters.
_NAME_EXTRA_CHARS = " -'"

# Region assumed when a phone number is given without a country code.
_DEFAULT_REGION = "PH"


def validate_name(name: str, label: str = "Name") -> str:
    """
    Validates first or last names:
    - 1-50 characters
    - Allows Unicode letters, hyphens, spaces, and apostrophes
    - Strips surrounding whitespace and collapses internal runs
    """
    # Collapses internal whitespace runs as well as stripping the ends
    name = " ".join(name.split())

    if len(name) < 1:
        raise ValueError(f"{label} cannot be empty")
    if len(name) > 50:
        raise ValueError(f"{label} is too long (max 50 characters)")

    # str.isalpha() is Unicode-aware, so accents and non-Latin scripts pass
    # while digits, symbols and punctuation do not.
    if not all(char.isalpha() or char in _NAME_EXTRA_CHARS for char in name):
        raise ValueError(f"{label} contains invalid characters")
    if not name[0].isalpha():
        raise ValueError(f"{label} must start with a letter")

    # Stored as typed: case-folding mangles names like "McDonald" and "DeLuca"
    return name


def name_validator(label: str) -> AfterValidator:
    """Builds a name validator that reports errors under a specific field label."""
    return AfterValidator(lambda value: validate_name(value, label))


def validate_password(password: str) -> str:
    """
    Validates password:
    - min 8 characters
    - must include uppercase, lowercase, and a digit
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not any(char.isupper() for char in password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(char.islower() for char in password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not any(char.isdigit() for char in password):
        raise ValueError("Password must contain at least one digit")
    return password


# Makes it optional
def validate_phone_number(phone_number: str | None) -> str | None:
    """
    - Validates phone number (Optional):
    - Accepts national or international formats, with spaces and dashes
    - Normalizes to E.164 (e.g. "+639123456789") so lookups and dedupe work
    """
    if phone_number is None:
        return None
    if not phone_number.strip():
        return None

    try:
        # parse from phonenumbers
        parsed = phonenumbers.parse(phone_number, _DEFAULT_REGION)
    except phonenumbers.NumberParseException as exc:
        raise ValueError(
            "Invalid phone number format. Use numeric format (e.g., +639123456789)"
        ) from exc

    if not phonenumbers.is_valid_number(parsed):
        raise ValueError("Invalid phone number")

    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


ValidatedPhone = Annotated[str | None, AfterValidator(validate_phone_number)]
ValidatedName = Annotated[str, AfterValidator(validate_name)]
ValidatedPassword = Annotated[str, AfterValidator(validate_password)]
ValidatedFirstName = Annotated[str, name_validator("First name")]
ValidatedLastName = Annotated[str, name_validator("Last name")]
