"""
Common Pydantic schemas for request/response models.
"""

from datetime import datetime
from typing import Optional, Generic, TypeVar, List
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID


# Generic type for pagination
T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        validate_assignment=True
    )


class TimestampMixin(BaseSchema):
    """Mixin for timestamps."""
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")


class UUIDMixin(BaseSchema):
    """Mixin for UUID identifier."""
    id: UUID = Field(description="Unique identifier")


class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, alias="pageSize", description="Items per page")

    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Get limit for database query."""
        return self.page_size


class PaginatedResponse(BaseSchema, Generic[T]):
    """Paginated response wrapper."""
    items: List[T] = Field(description="List of items")
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page")
    page_size: int = Field(alias="pageSize", description="Items per page")
    total_pages: int = Field(alias="totalPages", description="Total number of pages")

    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        page_size: int
    ) -> "PaginatedResponse[T]":
        """Create paginated response."""
        total_pages = (total + page_size - 1) // page_size
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )


class ErrorResponse(BaseSchema):
    """Standard error response."""
    error_code: str = Field(alias="errorCode", description="Error code")
    detail: str = Field(description="Error message")
    status_code: int = Field(alias="statusCode", description="HTTP status code")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseSchema):
    """Health check response."""
    status: str = Field(description="Service status")
    service: str = Field(description="Service name")
    version: str = Field(description="Service version")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    database: Optional[str] = Field(default=None, description="Database status")
    cache: Optional[str] = Field(default=None, description="Cache status")
    message_queue: Optional[str] = Field(default=None, alias="messageQueue", description="Message queue status")


class SuccessResponse(BaseSchema):
    """Generic success response."""
    success: bool = Field(default=True, description="Operation success")
    message: str = Field(description="Success message")
    data: Optional[dict] = Field(default=None, description="Optional response data")