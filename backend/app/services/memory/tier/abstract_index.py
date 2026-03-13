"""
Tier 1 Memory Layer: In-Memory Abstract Index
Provides sub-millisecond routing and filtering across all memory abstracts.

P2 — 长期记忆衰减机制 (Memory Temperature & Decay):
  每条记忆携带 `temperature` (热度) 字段，初始为 1.0。
  - 每次命中 (`increment_hit`) 时热度按固定步长提升（上限 1.0）。
  - 定时任务 `apply_decay` 按衰减系数对全量热度进行惩罚。
  - 热度降至阈值以下后由 `evict_cold` 从索引中清除。
"""

from datetime import datetime
from typing import Any

from loguru import logger

# Decay configuration constants
_DEFAULT_DECAY_RATE: float = 0.95      # Daily temperature multiplier
_HIT_BOOST: float = 0.10              # Temperature increment per access
_EVICTION_THRESHOLD: float = 0.05     # Remove entries below this temperature


class InMemoryAbstractIndex:
    """
    A fast, in-memory tier-1 index for memory abstracts.
    Uses inverted indices for O(1) property/tag lookups.

    Each abstract carries a `temperature` score that decays daily and rises
    on access, enabling automatic eviction of cold (rarely-used) memories.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
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

        self._initialized = True
        logger.info("⚡ In-Memory Abstract Index initialized.")

    def add_abstract(
        self,
        doc_id: str,
        title: str,
        doc_type: str,
        tags: list[str],
        timestamp: str | None = None,
    ) -> None:
        """
        Ingest a new abstract into memory and update all routing indices.
        New entries start with full temperature (1.0).
        """
        date_str = timestamp.split("T")[0] if timestamp else datetime.utcnow().strftime("%Y-%m-%d")

        abstract = {
            "id": doc_id,
            "title": title,
            "type": doc_type,
            "tags": tags,
            "date": date_str,
            # --- P2: Memory Temperature ---
            "temperature": 1.0,
            "hit_count": 0,
            "last_accessed": datetime.utcnow().isoformat(),
        }

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
        self,
        tags: list[str] | None = None,
        doc_types: list[str] | None = None,
        dates: list[str] | None = None,
        limit: int = 10,
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

    # ─────────────────────────────────────────────
    # P2: Memory Temperature API
    # ─────────────────────────────────────────────

    def increment_hit(self, doc_id: str, boost: float = _HIT_BOOST) -> None:
        """
        Record an access hit for the given doc_id:
          - Increments hit_count.
          - Boosts temperature (capped at 1.0).
          - Updates last_accessed timestamp.
        """
        entry = self.doc_store.get(doc_id)
        if entry is None:
            return
        entry["hit_count"] = entry.get("hit_count", 0) + 1
        entry["temperature"] = min(1.0, entry.get("temperature", 1.0) + boost)
        entry["last_accessed"] = datetime.utcnow().isoformat()

    def apply_decay(self, decay_rate: float = _DEFAULT_DECAY_RATE) -> int:
        """
        P2 — 每日热度时间衰减 (Time-based Weight Decay).

        对全量记忆条目的 temperature 乘以 decay_rate，模拟遗忘曲线。
        应由 Celery Beat 每日定时触发。

        Returns:
            int: Number of entries whose temperature dropped below the eviction threshold.
        """
        below_threshold = 0
        for entry in self.doc_store.values():
            current_temp = entry.get("temperature", 1.0)
            new_temp = round(current_temp * decay_rate, 6)
            entry["temperature"] = new_temp
            if new_temp < _EVICTION_THRESHOLD:
                below_threshold += 1
        logger.info(
            f"🌡️ [MemoryDecay] Applied decay (rate={decay_rate}). "
            f"{below_threshold}/{len(self.doc_store)} entries below eviction threshold."
        )
        return below_threshold

    def evict_cold(self, threshold: float = _EVICTION_THRESHOLD) -> int:
        """
        P2 — 冷数据驱逐 (Cold Memory Eviction).

        从索引中移除 temperature < threshold 的冷数据条目，
        防止无热度数据永久占用注入池。

        Returns:
            int: Number of evicted entries.
        """
        cold_ids = [doc_id for doc_id, entry in self.doc_store.items() if entry.get("temperature", 1.0) < threshold]

        for doc_id in cold_ids:
            entry = self.doc_store.pop(doc_id, {})

            # Remove from type index
            doc_type = entry.get("type")
            if doc_type and doc_type in self.type_index:
                self.type_index[doc_type].discard(doc_id)

            # Remove from date index
            date_str = entry.get("date")
            if date_str and date_str in self.date_index:
                self.date_index[date_str].discard(doc_id)

            # Remove from tag index
            for tag in entry.get("tags", []):
                tag_clean = tag.lower().strip()
                if tag_clean in self.tag_index:
                    self.tag_index[tag_clean].discard(doc_id)

        if cold_ids:
            logger.info(f"🧹 [MemoryEviction] Evicted {len(cold_ids)} cold memory entries (threshold={threshold}).")

        return len(cold_ids)

    def get_stats(self) -> dict:
        """Return summary stats for observability."""
        temps = [e.get("temperature", 1.0) for e in self.doc_store.values()]
        return {
            "total_entries": len(self.doc_store),
            "avg_temperature": round(sum(temps) / len(temps), 4) if temps else 0.0,
            "cold_count": sum(1 for t in temps if t < _EVICTION_THRESHOLD),
        }


# Singleton access
abstract_index = InMemoryAbstractIndex()
