"""
Backward Compatibility Proxy for app.core.exceptions.
Deprecated: Use app.sdk.core.HiveMindException instead.
"""
import warnings
from app.sdk.core import HiveMindException

warnings.warn(
    "Importing from app.core.exceptions is deprecated. Please use app.sdk.core instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ["HiveMindException"]
