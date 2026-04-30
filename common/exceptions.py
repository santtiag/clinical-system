"""
Custom exceptions for the Sistema Clínico application.
"""

from typing import Optional, Any
from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base exception for application errors."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: Optional[str] = None,
        headers: Optional[dict] = None
    ):
        super().__init__(
            status_code=status_code,
            detail=detail,
            headers=headers
        )
        self.error_code = error_code or f"ERR_{status_code}"

    def to_dict(self) -> dict:
        """Convert exception to dictionary for API response."""
        return {
            "error_code": self.error_code,
            "detail": self.detail,
            "status_code": self.status_code
        }


class NotFoundException(AppException):
    """Resource not found exception."""

    def __init__(
        self,
        resource: str,
        resource_id: Any,
        detail: Optional[str] = None
    ):
        message = detail or f"{resource} with id '{resource_id}' not found"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
            error_code="RESOURCE_NOT_FOUND"
        )
        self.resource = resource
        self.resource_id = resource_id


class ValidationException(AppException):
    """Data validation exception."""

    def __init__(self, detail: str, field: Optional[str] = None):
        message = f"{field}: {detail}" if field else detail
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=message,
            error_code="VALIDATION_ERROR"
        )


class UnauthorizedException(AppException):
    """Authentication required exception."""

    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="UNAUTHORIZED",
            headers={"WWW-Authenticate": "Bearer"}
        )


class ForbiddenException(AppException):
    """Access forbidden exception."""

    def __init__(self, detail: str = "Access denied"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="FORBIDDEN"
        )


class ConflictException(AppException):
    """Resource conflict exception (duplicate, etc.)."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="CONFLICT"
        )


class ServiceUnavailableException(AppException):
    """Service unavailable exception."""

    def __init__(self, service_name: str):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service '{service_name}' is temporarily unavailable",
            error_code="SERVICE_UNAVAILABLE"
        )


class InternalServerError(AppException):
    """Internal server error exception."""

    def __init__(self, detail: str = "An internal error occurred"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code="INTERNAL_ERROR"
        )