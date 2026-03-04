from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from app.core.vector_store import VectorDocument, SearchType

class RetrievalContext(BaseModel):
    """State object passed between Retrieval Steps."""
    # Input
    query: str
    kb_ids: List[str]
    user_id: Optional[str] = None
    is_admin: bool = False
    
    # Configuration
    top_k: int = 20
    top_n: int = 5
    search_type: str = SearchType.HYBRID
    
    # Query Understanding
    query_intent: str = "fact"
    rewritten_query: Optional[str] = None
    hyde_document: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    
    # Intermediate State
    expanded_queries: List[str] = Field(default_factory=list)
    sub_queries: List[str] = Field(default_factory=list) # Decomposed sub-questions
    candidates: List[VectorDocument] = Field(default_factory=list)
    
    # Final Output
    final_results: List[VectorDocument] = Field(default_factory=list)
    
    # Metadata / Logs
    trace_log: List[str] = Field(default_factory=list)

    def log(self, step_name: str, message: str):
        entry = f"[{step_name}] {message}"
        self.trace_log.append(entry)
