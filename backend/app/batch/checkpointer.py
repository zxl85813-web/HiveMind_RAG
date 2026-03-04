"""
模块级 docstring — 基于 Pickle 的文件持久化检查点。

所属模块: batch.checkpointer
依赖模块: langgraph.checkpoint.memory, pickle, os
注册位置: REGISTRY.md > Batch Engine > JobManager (Dependency)
"""
import pickle
import os
from typing import Any, AsyncIterator, Iterator, Optional, Sequence
from contextlib import asynccontextmanager

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata, CheckpointTuple, SerializerProtocol
from langgraph.checkpoint.memory import MemorySaver

class PickleCheckpointer(MemorySaver):
    """
    A persistent checkpointer that saves state to a local pickle file.
    Inherits from MemorySaver to reuse in-memory logic, but adds disk persistence.
    """
    def __init__(self, filepath: str = "checkpoints.pkl", serde: Optional[SerializerProtocol] = None):
        super().__init__(serde=serde)
        self.filepath = filepath
        self._load()

    def _load(self):
        """Load state from disk if exists."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "rb") as f:
                    data = pickle.load(f)
                    if isinstance(data, dict):
                        # Restore internal storage
                        # MemorySaver uses self.storage (dict) and self.writes (dict)
                        # We need to restore both if present
                        if "storage" in data:
                            self.storage = data["storage"]
                        if "writes" in data:
                            self.writes = data["writes"]
            except Exception as e:
                print(f"⚠️ Failed to load checkpoint file {self.filepath}: {e}")
                # Start fresh on error

    def _save(self):
        """Save state to disk."""
        try:
            # Create directory if needed
            os.makedirs(os.path.dirname(os.path.abspath(self.filepath)), exist_ok=True)
            
            data = {
                "storage": self.storage,
                "writes": self.writes
            }
            
            # Atomic write pattern
            temp_path = f"{self.filepath}.tmp"
            with open(temp_path, "wb") as f:
                pickle.dump(data, f)
            
            # Replace original file
            if os.path.exists(self.filepath):
                os.replace(temp_path, self.filepath)
            else:
                os.rename(temp_path, self.filepath)
                
        except Exception as e:
            print(f"❌ Failed to save checkpoint to {self.filepath}: {e}")

    def put(self, config: RunnableConfig, checkpoint: Checkpoint, metadata: CheckpointMetadata, new_versions: dict) -> RunnableConfig:
        """Save a checkpoint and persist to disk."""
        result = super().put(config, checkpoint, metadata, new_versions)
        self._save()
        return result

    async def aput(self, config: RunnableConfig, checkpoint: Checkpoint, metadata: CheckpointMetadata, new_versions: dict) -> RunnableConfig:
        """Async save a checkpoint and persist to disk."""
        result = await super().aput(config, checkpoint, metadata, new_versions)
        # Note: _save is synchronous (pickle dump), which might block event loop briefly.
        # But for MVP it's acceptable. Ideally run in executor.
        self._save()
        return result

    def put_writes(self, config: RunnableConfig, writes: Sequence[tuple[str, Any]], task_id: str, task_path: str = "") -> None:
        """Store intermediate writes and persist."""
        super().put_writes(config, writes, task_id, task_path)
        self._save()

    async def aput_writes(self, config: RunnableConfig, writes: Sequence[tuple[str, Any]], task_id: str, task_path: str = "") -> None:
        """Async store intermediate writes and persist."""
        await super().aput_writes(config, writes, task_id, task_path)
        self._save()
