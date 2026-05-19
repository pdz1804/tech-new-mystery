"""FastAPI exception handlers for domain errors."""

import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.exceptions import (
    AppError,
    UnauthorizedError,
    ForbiddenError,
    ArticleNotFoundError,
    UserNotFoundError,
    DuplicateError,
    ValidationError,
    NotFoundError,
)

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all custom exception handlers with FastAPI."""

    @app.exception_handler(UnauthorizedError)
    async def unauthorized_handler(
        request: Request, exc: UnauthorizedError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "error": {"code": exc.code, "message": exc.message},
            },
        )

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(request: Request, exc: ForbiddenError) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content={
                "success": False,
                "error": {"code": exc.code, "message": exc.message},
            },
        )

    @app.exception_handler(ArticleNotFoundError)
    async def article_not_found_handler(
        request: Request, exc: ArticleNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": {"code": exc.code, "message": exc.message},
            },
        )

    @app.exception_handler(UserNotFoundError)
    async def user_not_found_handler(
        request: Request, exc: UserNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": {"code": exc.code, "message": exc.message},
            },
        )

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": {"code": exc.code, "message": exc.message},
            },
        )

    @app.exception_handler(DuplicateError)
    async def duplicate_error_handler(
        request: Request, exc: DuplicateError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": f"{exc.field} already exists" if exc.field else exc.message,
                },
            },
        )

    @app.exception_handler(ValidationError)
    async def validation_error_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": {"code": exc.code, "message": exc.message},
            },
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = []
        for error in exc.errors():
            field = ".".join(str(x) for x in error["loc"][1:])
            errors.append(
                {
                    "field": field,
                    "message": error["msg"],
                    "type": error["type"],
                }
            )
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": errors,
                },
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        status_code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
            422: "VALIDATION_ERROR",
            500: "INTERNAL_SERVER_ERROR",
        }
        code = status_code_map.get(exc.status_code, "ERROR")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {"code": code, "message": exc.detail or "Request failed"},
            },
        )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        status_code = 500
        if isinstance(exc, DuplicateError):
            status_code = 409
        elif isinstance(exc, ValidationError):
            status_code = 422
        elif isinstance(exc, (ArticleNotFoundError, UserNotFoundError, NotFoundError)):
            status_code = 404
        elif isinstance(exc, UnauthorizedError):
            status_code = 401
        elif isinstance(exc, ForbiddenError):
            status_code = 403

        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "error": {"code": exc.code, "message": exc.message},
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Please try again later.",
                },
            },
        )
