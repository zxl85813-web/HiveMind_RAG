"""
DEPRECATED — historical placeholder.

This package was originally intended to host the RAG engine, but the actual
implementation lives elsewhere. Import from these locations instead:

    Retrieval pipeline   → app.services.retrieval
    Unified RAG gateway  → app.services.rag_gateway   (RAGGateway)
    Knowledge base mgmt  → app.services.knowledge
    Vector store layer   → app.core.vector_store
    Graph store layer    → app.core.graph_store

Kept only as an empty namespace to avoid breaking any stray import paths.
Will be removed once REGISTRY is updated and no references remain.
"""
