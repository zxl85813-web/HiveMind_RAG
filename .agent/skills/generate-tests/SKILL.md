---
name: generate-tests
description: Generate comprehensive test cases (dual-view) for a given backend or frontend file.
---

# 🎯 Generate Tests Skill

> **When to use**: When the user asks you to "write tests for X" or during the implementation phase of a feature, to automatically generate rigorous dual-view tests based on `.agent/rules/testing_guidelines.md`.

## 🛠 Prerequisites

1.  Read `.agent/rules/testing_guidelines.md` to understand the Testing Pyramid, Mock Decision Tree, and Dual-View approaches.
2.  Understand the target file you are generating tests for. If the user just gave a path, `view_file` the target path first.
3.  Look for equivalent fixture files in `backend/tests/conftest.py` if testing backend, or common rendering wrappers if testing frontend.

## 📝 Execution Steps

### Step 1: Analyze Target Context
- Identify if the file is a Python Backend Service, an API Route, or a React Frontend Component.
- List out all public methods/endpoints exported by the file.
- Identify the dependencies that are imported at the top of the file (database sessions, external APIs, etc.).

### Step 2: Determine Mocking Strategy
Apply the [Mock Decision Tree](../rules/testing_guidelines.md#04-mock-决策树-when-to-mock).
- Native core logic? Do not mock.
- LLM Call? Mock it.
- Session in an API Test? Use the SQLite memory session, do not mock.

### Step 3: Scaffold Test File
Create the test file at the mirror location dictated by the guidelines:
- `backend/app/services/xxx.py` -> `backend/tests/unit/services/test_xxx.py`
- `frontend/src/components/xxx/Yyy.tsx` -> `frontend/src/components/xxx/__tests__/Yyy.test.tsx`

### Step 4: Write Dual-View Tests
Generate tests that cover both viewpoints:
1.  **Contract View**: e.g., `test_xxx_success_flow_returns_apiresponse`
2.  **Logic/Resilience View**: e.g., `test_xxx_database_error_raises_500`

### Step 5: Implementation & Refinement
Write the actual assertion code. Make sure that Pydantic V2 models are instantiated correctly as per the pitfall warnings in the guidelines.

### Step 6: Inform the User
Output a markdown summary showing where the new test file was created, which branches it covers, and a suggested terminal command (like `pytest backend/tests/...`) for the user to run the tests locally.
