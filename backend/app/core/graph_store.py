"""
Backward Compatibility Proxy for app.core.graph_store.
Deprecated: Use app.sdk.core.graph_store instead.
"""
import warnings
from app.sdk.core.graph_store import Neo4jStore, get_graph_store

warnings.warn(
    "Importing from app.core.graph_store is deprecated. Please use app.sdk.core instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ["Neo4jStore", "get_graph_store"]
