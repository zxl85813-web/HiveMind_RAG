
import os
import time
import uuid
from typing import Literal, List, Optional, Dict, Any
from pydantic import BaseModel, Field
from pathlib import Path
from loguru import logger

from app.schemas.governance import EscalatedTask
from app.services.memory.social_graph_service import SocialGraphService

class EscalationManager:
    """
    L5 Governance Service: Manages the lifecycle of unresolved tasks,
    bridging the gap between Autonomous Execution and Human Oversight.
    """
    def __init__(self, project_root: Optional[Path] = None):
        # From backend/app/services/governance/escalation_manager.py to project root is 4 levels up to backend, then 1 more to root
        self.root = project_root or Path(__file__).resolve().parent.parent.parent.parent.parent
        self.todo_path = self.root / "TODO.md"
        self.tasks_dir = self.root / "docs" / "tasks"
        self.graph_service = SocialGraphService()
        
        # Ensure tasks directory exists
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

    async def report_task(self, task: EscalatedTask, swarm_state: Optional[Dict[str, Any]] = None) -> str:
        """
        Main entry point to report an unresolved problem.
        Performs triple persistence: TODO.md (Text), docs/tasks/ (Snapshot), and Neo4j (Graph).
        """
        logger.info(f"🚩 [Escalation] Reporting task: {task.task_id} - {task.title}")
        
        # 1. Generate Context Snapshot
        snapshot_path = await self._generate_snapshot(task, swarm_state)
        
        # 2. Append to TODO.md
        await self._append_to_todo(task, snapshot_path)
        
        # 3. Register in Knowledge Graph (Neo4j)
        await self.graph_service.register_escalated_task(task)
        
        return task.task_id

    async def _generate_snapshot(self, task: EscalatedTask, state: Optional[Dict[str, Any]]) -> Path:
        """
        Creates a 'Frozen Scene' of the agent's mind at the moment of escalation.
        """
        filename = f"{task.task_id}.snapshot.md"
        path = self.tasks_dir / filename
        
        content = [
            f"# 🧠 Escalation Snapshot: {task.task_id}",
            f"\n- **Title**: {task.title}",
            f"- **Priority**: {task.priority}",
            f"- **Trace ID**: {task.trace_id}",
            f"- **Created At**: {task.created_at}",
            "\n## 🔴 Problem Description",
            task.context_stub,
            "\n## 💡 Suggested Action",
            task.suggested_action,
        ]
        
        if state:
            content.append("\n## 🧊 Swarm State (Partial)")
            # Sanitize state for display (exclude large blobs)
            filtered_state = {k: v for k, v in state.items() if not isinstance(v, (list, dict)) or len(str(v)) < 500}
            content.append("```json")
            import json
            content.append(json.dumps(filtered_state, indent=2, ensure_ascii=False))
            content.append("```")
            
        path.write_text("\n".join(content), encoding="utf-8")
        return path

    async def _append_to_todo(self, task: EscalatedTask, snapshot_path: Path):
        """
        Registers the task in the physical TODO.md file under the Governance section.
        """
        if not self.todo_path.exists():
            logger.warning("TODO.md not found, skipping text append.")
            return

        # Find or create the [PENDING_HUMAN] section
        todo_content = self.todo_path.read_text(encoding="utf-8")
        
        section_header = "## 🤖 智体提报任务 (Agent-Escalated Tasks)"
        if section_header not in todo_content:
            # Add section before '待修复 Bug'
            if "## 🐛 待修复 Bug" in todo_content:
                todo_content = todo_content.replace("## 🐛 待修复 Bug", f"{section_header}\n\n## 🐛 待修复 Bug")
            else:
                todo_content += f"\n\n{section_header}\n"

        # Prepare new entry
        rel_snapshot = os.path.relpath(snapshot_path, self.root)
        new_entry = f"- [ ] **{task.task_id}**: {task.title} (Priority: {task.priority}) | [查看存根]({rel_snapshot})\n"
        
        # Inject entry after the header
        lines = todo_content.splitlines()
        try:
            header_idx = next(i for i, line in enumerate(lines) if section_header in line)
            lines.insert(header_idx + 1, new_entry)
            self.todo_path.write_text("\n".join(lines), encoding="utf-8")
        except StopIteration:
            logger.error(f"Failed to find header {section_header} in TODO.md")

escalation_manager = EscalationManager()
