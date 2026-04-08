"""
Backward Compatibility Proxy for app.core.token_service.
Deprecated: Use app.sdk.core.TokenService instead.
"""
import warnings
from app.sdk.core import TokenService

warnings.warn(
    "Importing from app.core.token_service is deprecated. Please use app.sdk.core instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ["TokenService"]
