"""
Common utilities for Sistema Clínico microservices.
Provides shared functionality: config, security, logging, database, messaging.
"""

from common.config import settings, Settings
from common.security import create_access_token, verify_password, get_password_hash, decode_token
from common.logging import setup_logging, get_logger
from common.database import get_db, init_db, BaseModel
from common.messaging import MessagePublisher, get_message_publisher
from common.exceptions import (
    AppException,
    NotFoundException,
    ValidationException,
    UnauthorizedException,
    ForbiddenException,
    ConflictException
)
from common.schemas import BaseSchema, PaginationParams

__all__ = [
    # Config
    "settings",
    "Settings",
    # Security
    "create_access_token",
    "verify_password",
    "get_password_hash",
    "decode_token",
    # Logging
    "setup_logging",
    "get_logger",
    # Database
    "get_db",
    "init_db",
    "BaseModel",
    # Messaging
    "MessagePublisher",
    "get_message_publisher",
    # Exceptions
    "AppException",
    "NotFoundException",
    "ValidationException",
    "UnauthorizedException",
    "ForbiddenException",
    "ConflictException",
    # Schemas
    "BaseSchema",
    "PaginationParams",
]

__version__ = "1.0.0"