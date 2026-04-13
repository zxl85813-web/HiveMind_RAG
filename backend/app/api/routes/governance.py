from typing import Any
from fastapi import APIRouter, Header, BackgroundTasks
from pydantic import BaseModel
from app.common.response import ApiResponse
from app.core.config import settings
import os
import time
import json
from loguru import logger

router = APIRouter()

class ProtocolIncident(BaseModel):
    category: str  # e.g., "contract_drift", "case_mismatch", "missing_field"
    component: str
    action: str
    data_sent: Any
    data_received: Any
    severity: str = "medium"
    stack_trace: str | None = None

def _archive_incident_task(incident: ProtocolIncident, trace_id: str):
    """异步将事故归档为 Markdown 文件并更新 TODO。"""
    incident_dir = os.path.join(settings.BASE_DIR, "docs", "governance", "incidents")
    os.makedirs(incident_dir, exist_ok=True)
    
    timestamp = int(time.time())
    filename = f"INCIDENT-{timestamp}-{trace_id[:8]}.md"
    filepath = os.path.join(incident_dir, filename)
    
    content = f"""# 🚨 Protocol Incident Report: {incident.category}

- **ID**: {filename}
- **Trace ID**: `{trace_id}`
- **Severity**: {incident.severity}
- **Component**: `{incident.component}`
- **Timestamp**: {time.ctime(timestamp)}

## 📝 Description
Detected a protocol inconsistency during `{incident.action}`.

## 🔍 Payload Analysis
### Data Sent (Frontend Request)
```json
{json.dumps(incident.data_sent, indent=2)}
```

### Data Received (Backend Response Artifact)
```json
{json.dumps(incident.data_received, indent=2)}
```

## 🛠️ Stack Trace / Context
```text
{incident.stack_trace or "No stack trace provided."}
```

---
*Targeted for automatic RCA by Governance Agent.*
"""
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    
    logger.warning(f"🔴 Governance Incident Recorded: {filepath}")
    
    # Update TODO.md
    todo_path = os.path.join(settings.BASE_DIR, "TODO.md")
    if os.path.exists(todo_path):
        with open(todo_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Insert after "## 🤖 智体提报任务" or at the bottom
        bug_index = -1
        for i, line in enumerate(lines):
            if "## 🤖 智体提报任务" in line:
                bug_index = i + 1
                break
        
        new_todo = f"- [ ] **{incident.category.upper()}**: Fix drift in `{incident.component}` (Ref: {filename}) | Priority: {incident.severity}\n"
        
        if bug_index != -1:
            lines.insert(bug_index, new_todo)
        else:
            lines.append("\n" + new_todo)
            
        with open(todo_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

@router.post("/incidents", response_model=ApiResponse)
async def report_incident(
    incident: ProtocolIncident, 
    background_tasks: BackgroundTasks,
    x_trace_id: str = Header(None)
):
    """
    接收前端上报的规约事故，并强制记录到文档库中。
    这是 L5 治理体系中的“强制自省”环。
    """
    background_tasks.add_task(_archive_incident_task, incident, x_trace_id or "unknown")
    return ApiResponse.ok(message="Incident captured and archived for analysis.")
