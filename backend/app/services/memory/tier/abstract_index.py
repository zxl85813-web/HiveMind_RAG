"""
Tier 1 Memory Layer: In-Memory Abstract Index
Provides sub-millisecond routing and filtering across all memory abstracts.
"""

from datetime import datetime
from typing import Any

from loguru import logger


class InMemoryAbstractIndex:
    """
    A fast, in-memory tier-1 index for memory abstracts.
    Uses inverted indices for O(1) property/tag lookups.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(InMemoryAbstractIndex, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # 1. The main document store (O(1) lookup by ID)
        self.doc_store: dict[str, dict[str, Any]] = {}

        # 2. Routing Indices (Inverted Indices mapping feature to Set of IDs)
        self.tag_index: dict[str, set[str]] = {}
        self.type_index: dict[str, set[str]] = {}
        self.date_index: dict[str, set[str]] = {}

        # Future: Simple inverted word index for title search if needed.

        self._initialized = True
        logger.info("⚡ In-Memory Abstract Index initialized.")

    def add_abstract(self, doc_id: str, title: str, doc_type: str, tags: list[str], timestamp: str = None) -> None:
        """
        Ingest a new abstract into memory and update all routing indices.
        """
        date_str = timestamp.split("T")[0] if timestamp else datetime.utcnow().strftime("%Y-%m-%d")

        abstract = {"id": doc_id, "title": title, "type": doc_type, "tags": tags, "date": date_str}

        # 1. Update doc store
        self.doc_store[doc_id] = abstract

        # 2. Update Type Index
        if doc_type not in self.type_index:
            self.type_index[doc_type] = set()
        self.type_index[doc_type].add(doc_id)

        # 3. Update Date Index
        if date_str not in self.date_index:
            self.date_index[date_str] = set()
        self.date_index[date_str].add(doc_id)

        # 4. Update Tag Index
        for tag in tags:
            tag_clean = tag.lower().strip()
            if tag_clean not in self.tag_index:
                self.tag_index[tag_clean] = set()
            self.tag_index[tag_clean].add(doc_id)

    def route_query(
        self, tags: list[str] = None, doc_types: list[str] = None, dates: list[str] = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Ultra-fast routing based on set intersections.
        Returns the matching abstract dictionaries.
        """
        # Start with all known IDs
        result_ids = set(self.doc_store.keys())
        if not result_ids:
            return []

        # 1. Filter by Type (Union of requested types)
        if doc_types:
            type_hits = set()
            for dt in doc_types:
                type_hits.update(self.type_index.get(dt, set()))
            # Intersect with running total
            result_ids.intersection_update(type_hits)

        # 2. Filter by Date (Union of requested dates)
        if dates and result_ids:
            date_hits = set()
            for d in dates:
                date_hits.update(self.date_index.get(d, set()))
            result_ids.intersection_update(date_hits)

        # 3. Filter by Tags
        # Depending on strictness, we can do AND (intersect all tags) or OR (union all tags)
        # For routing, OR (union) combined with ranking is usually best, but here we do AND for precision.
        if tags and result_ids:
            for tag in tags:
                tag_clean = tag.lower().strip()
                result_ids.intersection_update(self.tag_index.get(tag_clean, set()))
                if not result_ids:
                    break  # Early exit if intersection is empty

        # 4. Hydrate results and return
        results = [self.doc_store[did] for did in list(result_ids)[:limit]]

        # Optional: Sort by reverse date visually
        results.sort(key=lambda x: x.get("date", ""), reverse=True)
        return results


# Singleton access
abstract_index = InMemoryAbstractIndex()
