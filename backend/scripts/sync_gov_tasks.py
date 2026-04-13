
import os
import re
import asyncio
import sys
from typing import Optional
from pathlib import Path
from loguru import logger

# Add backend directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.sdk.core.graph_store import get_graph_store

class GovTaskSynchronizer:
    """
    Bi-directional Sync Engine:
    Ensures that manual updates in TODO.md are reflected in the Knowledge Graph,
    and vice-versa.
    """
    def __init__(self, project_root: Optional[Path] = None):
        self.root = project_root or Path(__file__).resolve().parent.parent.parent
        self.todo_path = self.root / "TODO.md"
        self.store = get_graph_store()
        
    async def sync(self):
        logger.info("🔄 [Sync] Starting Governance Task Synchronization...")
        
        if not self.todo_path.exists():
            logger.error("TODO.md not found.")
            return

        # 1. Parse TODO.md
        tasks_from_todo = self._parse_todo()
        logger.info(f"🔍 Found {len(tasks_from_todo)} escalated tasks in TODO.md")
        
        # 2. Update Neo4j based on TODO.md status
        for task_id, is_completed in tasks_from_todo.items():
            new_status = "RESOLVED" if is_completed else "PENDING"
            await self._update_graph_status(task_id, new_status)
            
        logger.info("✅ [Sync] TODO.md -> Graph synchronization complete.")

    def _parse_todo(self) -> dict[str, bool]:
        """
        Parses TODO.md to extract TASK-GOV IDs and their [x] status.
        Returns: { "TASK-GOV-XXXX": True/False }
        """
        content = self.todo_path.read_text(encoding="utf-8")
        # Target the specific section
        section_match = re.search(r"## 🤖 智体提报任务 (.*?)##", content, re.DOTALL)
        if not section_match:
            section_content = content.split("## 🤖 智体提报任务")[-1]
        else:
            section_content = section_match.group(1)

        # Regex to match task entries
        # Format: - [ ] **TASK-GOV-XXXX**: ...
        task_pattern = re.compile(r"- \[( |x|X)\] \*\*(TASK-GOV-[A-Z0-9]+)\*\*")
        
        tasks = {}
        for match in task_pattern.finditer(section_content):
            status_char, task_id = match.groups()
            tasks[task_id] = status_char.lower() == "x"
            
        return tasks

    async def _update_graph_status(self, task_id: str, status: str):
        """
        Updates the Task node status in Neo4j.
        """
        query = (
            "MATCH (t:Task {id: $task_id}) "
            "WHERE t.status <> $status "
            "SET t.status = $status, t.updated_at = timestamp() "
            "RETURN t.id as id"
        )
        res = await self.store.execute_query(query, {"task_id": task_id, "status": status})
        if res:
            logger.info(f"🆙 [Graph] Updated {task_id} to status {status}")

if __name__ == "__main__":
    from typing import Optional
    sync_engine = GovTaskSynchronizer()
    asyncio.run(sync_engine.sync())
