---
name: generate-tests
description: Generate comprehensive test cases (dual-view) for a given backend or frontend file.
---

# 🎯 Generate Tests Skill

> **When to use**: When the user asks you to "write tests for X" or during the implementation phase of a feature, to automatically generate rigorous dual-view tests based on `.agent/rules/testing_guidelines.md`.

## 📚 Skill Assets (Three-Layer Model)

### 1. Domain Library (`library/`)
- **testing-standards.md**: 测试规范（Mocking 准则、覆盖率要求、命名建议）。

### 2. Templates (`prompts/`)
- **test-template.j2**: Pytest 异步/同步测试模板。支持自动生成 Arrange-Act-Assert 结构。

### 3. Scripts (`scripts/`)
- **test-runner.py**: 自动化的单元测试运行器。生成测试代码后，务必运行此脚本进行闭环验证。

## 📝 Execution Steps (Enhanced)

### Step 1: Analyze & Context Ingestion
- Identify if the file is a Python Backend Service, an API Route, or a React Frontend Component.
- Read `library/testing-standards.md` to ensure mock strategy aligns with project rules.

### Step 2: Determine Mocking Strategy
- Apply the rules from the library to decide what dependencies to mock.
- Identify LLM calls, DB sessions, and External APIs.

### Step 3: Generation via Template
- Fill the variables for `prompts/test-template.j2`.
- Create the test file at the mirror location (e.g., `backend/tests/unit/...`).

### Step 4: Closed-loop Verification
- Run `python .agent/skills/generate-tests/scripts/test-runner.py <path_to_test_file>`.
- If tests fail, analyze output, fix the generated code, and re-run until passing.

### Step 5: Final Output
- Provide the final test code along with a summary of covered cases.
