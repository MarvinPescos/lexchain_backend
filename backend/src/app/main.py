from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.features.accounts import router as auth_router
from app.infrastructure.database.sessions import close_db
from app.infrastructure.observability.logging_setup import log
from app.shared.errors.exceptions import HTTP_ERROR_TYPES, BaseAppException, build_error_response


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_db()


app = FastAPI(lifespan=lifespan)


@app.exception_handler(BaseAppException)
async def app_exception_handler(request: Request, exc: BaseAppException):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
        headers=exc.headers,
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_response(
            error_type=HTTP_ERROR_TYPES.get(exc.status_code, "HTTPError"),
            message=str(exc.detail),
            status_code=exc.status_code,
        ),
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=build_error_response(
            error_type="ValidationError",
            message="Request validation failed",
            status_code=422,
            details={"errors": jsonable_encoder(exc.errors())},
        ),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    log.exception(
        "request.unhandled_exception",
        path=request.url.path,
        method=request.method,
    )
    return JSONResponse(
        status_code=500,
        content=build_error_response(
            error_type="InternalServerError",
            message="An unexpected error occurred.",
            status_code=500,
        ),
    )


app.include_router(auth_router)
