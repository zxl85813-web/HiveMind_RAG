---
name: generate-design-doc
description: 从需求文档 (REQ-NNN) 自动生成四级严谨设计说明书 (DES-NNN)
---

# 🏗️ Generate Design Doc Skill

> **When to use**: When a Requirement Document (REQ-NNN) is approved, and the user asks you to write the design or move to the architecture phase. 

## 🛠 Prerequisites

1.  Ask the user which Requirement Document (`docs/requirements/REQ-NNN.md`) they want to design for.
2.  `view_file` the REQ document to understand the goals, business flow, and boundary conditions.
3.  Read `.agent/rules/design-and-implementation-methodology.md` to ensure the generated design complies with the 4-tier rules.

## 📝 Execution Steps

### Step 1: Draft Database Design 
- Define the entities needed. Do they already exist in `backend/app/models/`? Provide exact paths.
- Draw a Mermaid ER Diagram containing all related entities, primary keys, foreign keys, and relationships.

### Step 2: Draft Backend Logic
- List out which services need to be added or modified in `backend/app/services/`.
- Draw a simple dependency tree (who calls whom) to ensure NO circular dependencies.
- List all exceptions (e.g., `DocumentTooLargeError`) that this module might throw.

### Step 3: Draft API Design
- Define the RESTful routes, following the naming convention in `api-design-standards.md`.
- Specify Request Schemas and Response Schemas. Do not detail all types unless critical. Remind that all models will be wrapped in `ApiResponse`.

### Step 4: Draft Frontend Component Tree
- Sketch the Smart/Dumb component hierarchy.
- **MANDATORY**: Search `component-inventory.md` or grep `components/common/` to find reusable UI components (e.g., `StatCard`, `ConfirmAction`). State explicitly which standard components will be used.

### Step 5: Save and Review
Write out the complete markdown into `docs/design/DES-NNN-<slug>.md`.
Notify the user to review the document and apply the "Multi-Perspective Review" criteria defined in the methodology.
