"""
Global exception handlers for FastAPI.
Converts exceptions to consistent JSON error responses.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
from jose import JWTError
import logging

from app.core.exceptions import (
    AppException,
    ValidationError,
    AuthenticationError,
    ConflictError,
    InternalError
)

logger = logging.getLogger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle all custom application exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors from request bodies."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " -> ".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid input data",
                "details": {"errors": errors}
            }
        }
    )


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """Handle database integrity errors (duplicates, constraint violations)."""
    error_message = str(exc.orig)

    # Check for duplicate key violations
    if "duplicate key" in error_message.lower() or "unique constraint" in error_message.lower():
        # Extract field name if possible
        if "email" in error_message.lower():
            message = "Email already exists"
        elif "slug" in error_message.lower():
            message = "Slug already exists"
        else:
            message = "Duplicate entry detected"

        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": {
                    "code": "ALREADY_EXISTS",
                    "message": message,
                    "details": {}
                }
            }
        )

    # Generic integrity error
    logger.error(f"Database integrity error: {error_message}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Database constraint violation",
                "details": {}
            }
        }
    )


async def jwt_error_handler(request: Request, exc: JWTError) -> JSONResponse:
    """Handle JWT token errors."""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": {
                "code": "UNAUTHORIZED",
                "message": "Invalid or expired token",
                "details": {}
            }
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unexpected exceptions."""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": {}
            }
        }
    )


def register_exception_handlers(app):
    """Register all exception handlers with the FastAPI app."""
    # Custom application exceptions
    app.add_exception_handler(AppException, app_exception_handler)

    # Pydantic validation errors
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # Database integrity errors
    app.add_exception_handler(IntegrityError, integrity_error_handler)

    # JWT errors
    app.add_exception_handler(JWTError, jwt_error_handler)

    # Generic catch-all
    app.add_exception_handler(Exception, generic_exception_handler)
