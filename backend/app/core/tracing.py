"""
Backward Compatibility Proxy for app.core.tracing.
Deprecated: Use app.sdk.core.get_tracer instead.
"""
import warnings
from app.sdk.core import get_tracer

warnings.warn(
    "Importing from app.core.tracing is deprecated. Please use app.sdk.core instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ["get_tracer"]
