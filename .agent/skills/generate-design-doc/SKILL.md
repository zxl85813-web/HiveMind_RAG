---
name: generate-design-doc
description: 从需求文档 (REQ-NNN) 自动生成四级严谨设计说明书 (DES-NNN)
---

# 🏗️ Generate Design Doc Skill

> **When to use**: When a Requirement Document (REQ-NNN) is approved, and the user asks you to write the design or move to the architecture phase. 

## 📚 Skill Assets (Three-Layer Model)

### 1. Domain Library (`library/`)
- **design-principles.md**: 核心架构准则（4-Tier Contract, No Circular Deps）。执行前建议先阅读此库以确保合规。

### 2. Templates (`prompts/`)
- **des-template.j2**: 标准化设计文档 Jinja2 模板。生成文档时务必参考此结构。

### 3. Scripts (`scripts/`)
- **validate-design-coherence.py**: 自动化的设计合规性校验脚本。完成初稿后，建议通过 `python_interpreter` 或 `programmatic_execute` 运行此脚本。

## 📝 Execution Steps (Enhanced)

### Step 1: Initialize & Knowledge Ingestion
- Ask the user which Requirement Document (`docs/requirements/REQ-NNN.md`) they want to design for.
- Read `library/design-principles.md` to load architecture constraints.

### Step 2: Drafting based on Template
- Use `prompts/des-template.j2` as the foundation for writing `docs/design/DES-NNN-<slug>.md`.
- Ensure Mermaid diagrams for Flow and ER are included as per the template.

### Step 3: Self-Validation (Programmatic Mode)
- Run `python .agent/skills/generate-design-doc/scripts/validate-design-coherence.py <path_to_des_md>` to check for common omissions.
- If errors are found, fix them before notifying the user.

### Step 4: Final Publish
- Notify the user to review.
