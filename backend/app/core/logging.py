"""
Backward Compatibility Proxy for app.core.logging.
Deprecated: Use app.sdk.core.logging instead.
"""
import warnings
from app.sdk.core.logging import (
    get_trace_logger, 
    logger, 
    setup_logging, 
    setup_script_context, 
    trace_id_var
)

warnings.warn(
    "Importing from app.core.logging is deprecated. Please use app.sdk.core instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ["get_trace_logger", "logger", "setup_logging", "setup_script_context", "trace_id_var"]
