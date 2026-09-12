from datetime import UTC, datetime
from typing import Any


def build_error_response(
    error_type: str, message: str, status_code: int, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Single source of Truth for error response formatting."""
    return {
        "error_type": error_type,
        "message": message,
        "status_code": status_code,
        "details": details,
        "timestamp": datetime.now(UTC).isoformat(),
    }
