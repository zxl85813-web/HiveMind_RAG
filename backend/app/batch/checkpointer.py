"""
模块级 docstring — 基于 Pickle 的文件持久化检查点。

所属模块: batch.checkpointer
依赖模块: langgraph.checkpoint.memory, pickle, os
注册位置: REGISTRY.md > Batch Engine > JobManager (Dependency)
"""

import json
import os
from collections.abc import Sequence
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata, SerializerProtocol
from langgraph.checkpoint.memory import MemorySaver


class SafeJsonEncoder(json.JSONEncoder):
    """Custom encoder to handle non-JSON types like bytes or timestamps if needed."""
    def default(self, obj):
        if isinstance(obj, bytes):
            return {"__bytes__": obj.hex()}
        return super().default(obj)

def safe_json_hook(dct):
    """Custom hook to restore non-JSON types."""
    if "__bytes__" in dct:
        return bytes.fromhex(dct["__bytes__"])
    return dct


class JsonCheckpointer(MemorySaver):
    """
    A persistent checkpointer that saves state to a local JSON file.
    Replaces PickleCheckpointer to mitigate RCE risks (SEC005).
    """

    def __init__(self, filepath: str = "checkpoints.json", serde: SerializerProtocol | None = None):
        super().__init__(serde=serde)
        self.filepath = filepath
        self._load()

    def _load(self):
        """Load state from disk if exists using safe JSON."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, encoding="utf-8") as f:
                    data = json.load(f, object_hook=safe_json_hook)
                    if isinstance(data, dict):
                        # Restore internal storage
                        if "storage" in data:
                            self.storage = data["storage"]
                        if "writes" in data:
                            self.writes = data["writes"]
            except Exception as e:
                print(f"⚠️ Failed to load checkpoint file {self.filepath}: {e}")

    def _save(self):
        """Save state to disk safely."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.filepath)), exist_ok=True)

            data = {"storage": self.storage, "writes": self.writes}

            temp_path = f"{self.filepath}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, cls=SafeJsonEncoder, indent=2)

            if os.path.exists(self.filepath):
                os.replace(temp_path, self.filepath)
            else:
                os.rename(temp_path, self.filepath)

        except Exception as e:
            print(f"❌ Failed to save checkpoint to {self.filepath}: {e}")

    def put(
        self, config: RunnableConfig, checkpoint: Checkpoint, metadata: CheckpointMetadata, new_versions: dict
    ) -> RunnableConfig:
        """Save a checkpoint and persist to disk."""
        result = super().put(config, checkpoint, metadata, new_versions)
        self._save()
        return result

    async def aput(
        self, config: RunnableConfig, checkpoint: Checkpoint, metadata: CheckpointMetadata, new_versions: dict
    ) -> RunnableConfig:
        """Async save a checkpoint and persist to disk."""
        result = await super().aput(config, checkpoint, metadata, new_versions)
        # Note: _save is synchronous (pickle dump), which might block event loop briefly.
        # But for MVP it's acceptable. Ideally run in executor.
        self._save()
        return result

    def put_writes(
        self, config: RunnableConfig, writes: Sequence[tuple[str, Any]], task_id: str, task_path: str = ""
    ) -> None:
        """Store intermediate writes and persist."""
        super().put_writes(config, writes, task_id, task_path)
        self._save()

    async def aput_writes(
        self, config: RunnableConfig, writes: Sequence[tuple[str, Any]], task_id: str, task_path: str = ""
    ) -> None:
        """Async store intermediate writes and persist."""
        await super().aput_writes(config, writes, task_id, task_path)
        self._save()
