from pydantic import BaseModel, Field

from app.core.vector_store import SearchType, VectorDocument
from app.schemas.auth import AuthorizationContext


class RetrievalContext(BaseModel):
    """State object passed between Retrieval Steps."""

    # Authorization
    auth_context: AuthorizationContext | None = None

    # Input
    query: str
    kb_ids: list[str]
    user_id: str | None = None
    is_admin: bool = False

    # Configuration
    top_k: int = 20
    top_n: int = 5
    search_type: str = SearchType.HYBRID

    # Query Understanding
    query_intent: str = "fact"
    rewritten_query: str | None = None
    hyde_document: str | None = None
    keywords: list[str] = Field(default_factory=list)

    # Intermediate State
    expanded_queries: list[str] = Field(default_factory=list)
    sub_queries: list[str] = Field(default_factory=list)  # Decomposed sub-questions
    candidates: list[VectorDocument] = Field(default_factory=list)
    graph_facts: list[str] = Field(default_factory=list)
    alignment_report: str | None = None

    # Final Output
    final_results: list[VectorDocument] = Field(default_factory=list)

    # Metadata / Logs
    trace_log: list[str] = Field(default_factory=list)

    def log(self, step_name: str, message: str):
        entry = f"[{step_name}] {message}"
        self.trace_log.append(entry)
