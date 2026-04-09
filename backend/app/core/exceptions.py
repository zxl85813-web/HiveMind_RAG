"""
Backward Compatibility Proxy for app.core.exceptions.
Deprecated: Use app.sdk.core.HiveMindException instead.
"""
import warnings
from app.sdk.core.exceptions import (
    AppError,
    AuthenticationError,
    ConflictError,
    ExternalServiceError,
    ForbiddenError,
    HiveMindException,
    NotFoundError,
    PermissionError,
    ValidationError,
)

__all__ = [
    "AppError",
    "AuthenticationError",
    "ConflictError",
    "ExternalServiceError",
    "ForbiddenError",
    "HiveMindException",
    "NotFoundError",
    "PermissionError",
    "ValidationError",
]
