import os
import re
from pathlib import Path

BASE_DIR = Path(r"c:\Users\linkage\Desktop\aiproject")

def test_regex():
    todo_file = BASE_DIR / "TODO.md"
    with open(todo_file, encoding="utf-8") as f:
        content = f.read()
    
    # regex matches: - [ ] **TASK-NAME**：Description
    pattern = r"- \[( |x|🟡|✅|⬜)\] \*\*([^*]+)\*\*：(.*?)(?:\（协作者: (.*?)\）|$)"
    matches = list(re.finditer(pattern, content))
    print(f"Found {len(matches)} list matches")
    for m in matches[:5]:
        print(f"ID: {m.group(2)}, Title: {m.group(3)}, Assignee: {m.group(4)}")

    # table matches: | TASK-NAME | Description | Assignee |
    table_pattern = r"\| \s*(TASK-[^|]+) \s* \| \s* ([^|]+) \s* \| \s* ([^|]+) \s* \|"
    table_matches = list(re.finditer(table_pattern, content))
    print(f"\nFound {len(table_matches)} table matches")
    for m in table_matches[:5]:
        print(f"ID: {m.group(1).strip()}, Title: {m.group(2).strip()}, Assignee: {m.group(3).strip()}")

test_regex()
