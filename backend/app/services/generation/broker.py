from typing import Any, Dict, Tuple, Optional
from app.core.logging import get_trace_logger

logger = get_trace_logger(__name__)

class ContextBroker:
    """
    Unified Context Broker (Phase 2 - VFS).
    Supports hierarchical path isolation (viking:// protocol).
    This simulates a scoped filesystem for Agent Context.
    """
    def __init__(self):
        self._tree: Dict[str, Any] = {
            "global": {},
            "sessions": {},
            "agents": {}
        }
    
    def _parse_path(self, path: str, create: bool = False) -> Optional[Tuple[Dict[str, Any], str]]:
        """
        Parses viking:// path and navigates the tree.
        Example: viking://sessions/task-123/shared/docs
        """
        clean_path = path.replace("viking://", "").strip("/")
        parts = clean_path.split("/")
        
        curr = self._tree
        # Navigate to the parent node
        for p in parts[:-1]:
            if p not in curr:
                if create:
                    curr[p] = {}
                else:
                    return None
            curr = curr[p]
        
        return curr, parts[-1]
    
    def page_out(self, path: str, payload: Any):
        """Writes data to a specific VFS path."""
        res = self._parse_path(path, create=True)
        if res:
            node, key = res
            logger.debug(f"VFS WRITE -> {path} (Type: {type(payload).__name__})")
            node[key] = payload
        
    def page_in(self, path: str, default: Any = None) -> Any:
        """Reads data from a specific VFS path."""
        res = self._parse_path(path)
        if res:
            node, key = res
            val = node.get(key, default)
            logger.debug(f"VFS READ  <- {path} (Match: {val is not default})")
            return val
        return default
        
    def clear(self, path: str):
        """Deletes a node or leaf in the VFS tree."""
        res = self._parse_path(path)
        if res:
            node, key = res
            if key in node:
                logger.debug(f"VFS CLEAR -- {path}")
                del node[key]

    def list_dir(self, path: str) -> list[str]:
        """Lists keys at a specific VFS path (analogous to ls)."""
        clean_path = path.replace("viking://", "").strip("/")
        parts = [p for p in clean_path.split("/") if p]
        
        curr = self._tree
        for p in parts:
            if not isinstance(curr, dict) or p not in curr:
                return []
            curr = curr[p]
            
        return list(curr.keys()) if isinstance(curr, dict) else []

# Global Instance
broker = ContextBroker()
