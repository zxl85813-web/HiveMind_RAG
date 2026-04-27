"""
Backward Compatibility Proxy for app.core.config.
Deprecated: Use app.sdk.core.settings instead.
"""
import warnings
# @covers REQ-014
from pydantic_settings import BaseSettings
from app.sdk.core import settings

warnings.warn(
    "Importing from app.core.config is deprecated. Please use app.sdk.core instead.",
    DeprecationWarning,
    stacklevel=2
)

# Proxy all common attributes
__all__ = ["settings"]
