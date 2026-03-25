import sys
from pathlib import Path
import json

# Add skill-creator to path so we can import his scripts if needed
# But for now let's just copy the logic
def embed_file(path: Path) -> dict:
    return {"name": path.name, "type": "text", "content": "mock"}

def build_run(root: Path, run_dir: Path) -> dict | None:
    outputs_dir = run_dir / "outputs"
    output_files = []
    if outputs_dir.is_dir():
        for f in sorted(outputs_dir.iterdir()):
            if f.is_file():
                output_files.append({"name": f.name})
    return {"id": str(run_dir.relative_to(root)), "outputs": output_files}

def _find_runs_recursive(root: Path, current: Path, runs: list[dict]) -> None:
    if not current.is_dir():
        return
    outputs_dir = current / "outputs"
    if outputs_dir.is_dir():
        run = build_run(root, current)
        if run:
            runs.append(run)
        return
    for child in sorted(current.iterdir()):
        if child.is_dir():
            _find_runs_recursive(root, child, runs)

runs = []
workspace = Path("skills/backend-expert-workspace/iteration-1")
_find_runs_recursive(workspace, workspace, runs)
print(json.dumps(runs, indent=2))
