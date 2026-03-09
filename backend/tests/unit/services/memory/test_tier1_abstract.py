from app.services.memory.tier.abstract_index import abstract_index

# ⚠️ This is an Agent-Generated Unit Test based on: docs/design/multi_tier_memory.md
# 🧠 Objective: Verify Tier 1 (Abstract Layer) routing speed and correctness.


def test_abstract_index_singleton_initialization():
    """Verify that multiple imports resolve to the same index instance."""
    from app.services.memory.tier.abstract_index import InMemoryAbstractIndex

    index1 = abstract_index
    index2 = InMemoryAbstractIndex()
    assert id(index1) == id(index2), "InMemoryAbstractIndex must be a Singleton"
    assert index1._initialized is True


def test_add_and_route_abstract_by_tags():
    """Verify O(1) tag routing works correctly."""

    # 1. Arrange Data
    abstract_index.add_abstract("DOC-1", "Test DB Bug", "log", ["database", "bug"], "2026-02-20")
    abstract_index.add_abstract("DOC-2", "Test FE Feature", "feature", ["frontend", "react"], "2026-02-20")
    abstract_index.add_abstract("DOC-3", "General Neo4j error", "log", ["database", "neo4j", "bug"], "2026-02-19")

    # 2. Act: Query only database bugs
    hits = abstract_index.route_query(tags=["database", "bug"])

    # 3. Assert
    assert len(hits) == 2
    # Ensure both returned documents have the required tags
    found_ids = [h["id"] for h in hits]
    assert "DOC-1" in found_ids
    assert "DOC-3" in found_ids
    assert "DOC-2" not in found_ids


def test_route_abstract_by_date_and_type():
    """Verify filtering by specific dates and document types."""
    abstract_index.add_abstract("DOC-1", "Test DB Bug", "log", ["database"], "2026-02-20")
    abstract_index.add_abstract("DOC-2", "Test DB Another", "log", ["database"], "2026-02-19")
    abstract_index.add_abstract("DOC-3", "System Query", "user_query", ["database"], "2026-02-20")

    # Only look for Logs on Feb 20
    hits = abstract_index.route_query(tags=["database"], doc_types=["log"], dates=["2026-02-20"])

    # DOC-1 matches all criteria
    # DOC-2 is wrong date
    # DOC-3 is wrong type
    assert len(hits) == 1
    assert hits[0]["id"] == "DOC-1"
