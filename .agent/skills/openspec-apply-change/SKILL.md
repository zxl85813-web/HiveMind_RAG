---
name: openspec-apply-change
description: Implement tasks from an OpenSpec change. Use when the user wants to start implementing, continue implementation, or work through tasks.
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  generatedBy: "1.2.0"
---

## 📚 Skill Assets (Three-Layer Model)

### 1. Knowledge Library (`library/`)
- **implementation-guardrails.md**: 实施守则（最小变更原则、错误处理策略）。

### 2. Scripts (`scripts/`)
- **task-verifier.py**: 自动化任务验证器，能自动提取并运行 `tasks.md` 中的验证指令。

## 📝 Execution Steps (Enhanced)

### Step 1: Context Loading & Selection
- Select the change to implement (or suggest available ones).
- Read `library/implementation-guardrails.md` to establish the safety boundary.

### Step 2: Incremental Implementation
- Loop through pending tasks from the chosen change.
- Perform minimal code changes for the current task.
- Update the checkbox `- [ ]` to `- [x]` in the artifact file.

### Step 3: Loopback Verification (Crucial)
- Run `python .agent/skills/openspec-apply-change/scripts/task-verifier.py <name>`.
- **Constraint**: If verification fails, stop and fix before proceeding to the next task.

### Step 4: Status Report
- Summarize tasks completed and overall progress.
- Suggest archiving if all tasks are done.
