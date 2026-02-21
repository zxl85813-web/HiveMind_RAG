from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from app.core.vector_store import VectorDocument, SearchType

class RetrievalContext(BaseModel):
    """State object passed between Retrieval Steps."""
    # Input
    query: str
    kb_ids: List[str]
    
    # Configuration
    top_k: int = 20
    top_n: int = 5
    search_type: str = SearchType.HYBRID
    
    # Intermediate State
    expanded_queries: List[str] = Field(default_factory=list)
    candidates: List[VectorDocument] = Field(default_factory=list)
    
    # Final Output
    final_results: List[VectorDocument] = Field(default_factory=list)
    
    # Metadata / Logs
    trace_log: List[str] = Field(default_factory=list)

    def log(self, step_name: str, message: str):
        entry = f"[{step_name}] {message}"
        self.trace_log.append(entry)
