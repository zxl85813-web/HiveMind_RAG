import os
import json
import pytest
from backend.app.batch.checkpointer import JsonCheckpointer
from langchain_core.runnables import RunnableConfig

@pytest.fixture
def temp_checkpoint_file(tmp_path):
    return str(tmp_path / "test_checkpoints.json")

class TestJsonCheckpointer:

    def test_save_load_basic_data(self, temp_checkpoint_file):
        """Contract View: Verifies standard data persistence."""
        checkpointer = JsonCheckpointer(filepath=temp_checkpoint_file)
        
        # Manually set some state (simulating MemorySaver storage)
        checkpointer.storage = {"thread_1": {"data": "foo"}}
        checkpointer.writes = {"thread_1": [("step_1", "bar")]}
        
        # Trigger explicit save
        checkpointer._save()
        
        # Create a new instance to load from same file
        new_checkpointer = JsonCheckpointer(filepath=temp_checkpoint_file)
        assert new_checkpointer.storage == {"thread_1": {"data": "foo"}}
        assert new_checkpointer.writes == {"thread_1": [("step_1", "bar")]}

    def test_binary_data_serialization(self, temp_checkpoint_file):
        """Logic/Resilience View: Verifies custom bytes encoding/decoding."""
        checkpointer = JsonCheckpointer(filepath=temp_checkpoint_file)
        
        binary_blob = b"hello \x00 world"
        checkpointer.storage = {"binary_key": binary_blob}
        
        checkpointer._save()
        
        # Check raw JSON file to see if it's hex-encoded
        with open(temp_checkpoint_file, "r") as f:
            raw_data = json.load(f)
            # The custom encoder should have turned it into {"__bytes__": "..."}
            assert "__bytes__" in raw_data["storage"]["binary_key"]
            assert raw_data["storage"]["binary_key"]["__bytes__"] == binary_blob.hex()

        # Reload and verify type restoration
        new_checkpointer = JsonCheckpointer(filepath=temp_checkpoint_file)
        assert isinstance(new_checkpointer.storage["binary_key"], bytes)
        assert new_checkpointer.storage["binary_key"] == binary_blob

    def test_corrupted_json_handling(self, temp_checkpoint_file):
        """Resilience View: Verifies graceful degradation on invalid files."""
        # Create a corrupted JSON file
        with open(temp_checkpoint_file, "w") as f:
            f.write("{ invalid json content ...")
            
        # Should not crash during init
        checkpointer = JsonCheckpointer(filepath=temp_checkpoint_file)
        # Should start with empty state
        assert checkpointer.storage == {}
        
    @pytest.mark.asyncio
    async def test_async_aput_triggers_save(self, temp_checkpoint_file):
        """Lifecycle View: Verifies apurt correctly persists to disk."""
        checkpointer = JsonCheckpointer(filepath=temp_checkpoint_file)
        
        config = RunnableConfig(configurable={"thread_id": "async_1"})
        checkpoint = {"v": 1, "ts": "2026-03-13"}
        metadata = {"source": "test"}
        
        # Call the async put method (inherits from MemorySaver but we overridden to add _save)
        await checkpointer.aput(config, checkpoint, metadata, {})
        
        # Verify file exists
        assert os.path.exists(temp_checkpoint_file)
        
        # Reload and verify
        new_checkpointer = JsonCheckpointer(filepath=temp_checkpoint_file)
        # MemorySaver.aput saves into its internal storage
        # We check if it survived the reload
        assert len(new_checkpointer.storage) > 0
