"""IP-based rate limiting for the API.

Owns the single `Limiter` the whole application shares. It uses slowapi's
default in-memory storage, which is only accurate because the service runs as
one uvicorn process (see docker-compose.yml); the counters live in that
process's heap and are not shared with anything else.
"""

from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import Response

from app.core import settings
from app.shared.errors.responses import build_error_response

# slowapi raises its own RateLimitExceeded before any application code runs, so
# there is no BaseAppException subclass whose name can fill the envelope's
# error_type. Spelled out here to match the "<Name>Error" shape the other
# handlers in main.py produce.
RATE_LIMIT_ERROR_TYPE = "TooManyRequestsError"

limiter = Limiter(
    # Keyed on the client IP: these routes are unauthenticated, so there is no
    # user id to key on at the point the limit has to be decided.
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    # Send X-RateLimit-* and Retry-After so a client can back off on a number
    # instead of guessing.
    headers_enabled=True,
    enabled=settings.RATE_LIMIT_ENABLED,
)


# Deliberately a plain `def`. SlowAPIMiddleware resolves the handler through a
# synchronous path and silently falls back to slowapi's own {"error": ...} body
# whenever the registered handler is a coroutine — which would leak a second
# error shape for every route that has no decorator of its own.
def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Render a 429 in the application's shared error envelope.

    Args:
        request: The request that tripped the limit.
        exc: The slowapi error carrying the limit that was hit.

    Returns:
        A 429 JSONResponse in the same shape ``build_error_response`` produces,
        carrying slowapi's X-RateLimit-* and Retry-After headers.
    """
    response = JSONResponse(
        status_code=429,
        content=build_error_response(
            error_type=RATE_LIMIT_ERROR_TYPE,
            message=f"Rate limit exceeded: {exc.detail}. Please try again later.",
            status_code=429,
        ),
    )
    # `_inject_headers` is private but it is what slowapi's own default handler
    # calls; there is no public equivalent. `view_rate_limit` is set just before
    # the error is raised, and is read defensively so a missing one degrades to
    # a header-less 429 rather than a 500 inside the error path.
    return limiter._inject_headers(response, getattr(request.state, "view_rate_limit", None))
