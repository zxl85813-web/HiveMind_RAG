---
name: openspec-propose
description: Propose a new change with all artifacts generated in one step. Use when the user wants to quickly describe what they want to build and get a complete proposal with design, specs, and tasks ready for implementation.
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  generatedBy: "1.2.0"
---

## 📚 Skill Assets (Three-Layer Model)

### 1. Knowledge Library (`library/`)
- **spec-writing-guide.md**: OpenSpec 编写最佳实践（MECE 原则、原子任务定义）。

### 2. Scripts (`scripts/`)
- **verify-spec.py**: 检查 OpenSpec Change 目录的完整性与合规性。

## 📝 Execution Steps (Enhanced)

### Step 1: Initialization & Context
- Ask the user what they want to build. Derive the `kebab-case-name`.
- Read `library/spec-writing-guide.md` to refresh memory on spec quality standards.

### Step 2: Create Change & Generate Artifacts
- Run `openspec new change "<name>"`.
- Iterate through artifacts (proposal -> design -> tasks).
- For each artifact, ensure the content adheres to the *OpenSpec Writing Guide*.

### Step 3: Consistency Audit
- Run `python .agent/skills/openspec-propose/scripts/verify-spec.py <name>`.
- Fix any missing linkages or structural errors.

### Step 4: Final Publish
- Summary of created artifacts and the next command: `/opsx:apply`.

---
