---
description: 版本里程碑时的代码自省(review)和自查(lint+test)流程
---

# 🔍 代码自省与自查流程

> **时机**: 在达到版本里程碑时执行，不是每次代码变更都执行。
> 典型触发点: 完成一个 REQ 需求的开发后、准备发版前。

## 阶段一: 自查 (Automated Checks)

### 1. 代码质量检查 (Code Quality System)

#### 快速检查 (仅 Lint)
```powershell
// turbo
python .agent/checks/code_quality.py --backend --frontend
```

#### 完整检查 (含安全扫描、复杂度分析、重复代码检测)
```powershell
python .agent/checks/code_quality.py --verbose --report
```

#### 自动修复
```powershell
python .agent/checks/code_quality.py --fix
```

#### PowerShell 快捷方式
```powershell
# 快速 lint
.\.agent\checks\run_checks.ps1 -Quick
# 完整检查 + HTML 报告
.\.agent\checks\run_checks.ps1 -Report -Verbose
```

> 📄 HTML 报告输出: `.agent/checks/reports/quality-report-*.html`


### 2. 一致性检查 (Custom)
手动或脚本检查以下项:

- [ ] **日志**: 所有文件用 `loguru.logger`，没有 `print()` 或 `logging`
- [ ] **配置**: 所有配置通过 `settings` 访问，没有硬编码或 `os.environ`
- [ ] **HTTP**: 所有 HTTP 请求用 `httpx`，没有 `requests`
- [ ] **前端样式**: 所有样式用 CSS 变量，没有硬编码色值
- [ ] **前端组件**: 所有 UI 用 Ant Design，没有原生 HTML 控件替代
- [ ] **API 层**: 所有请求通过 `services/` 层，组件内没有直接 `fetch/axios`
- [ ] **Schema**: 所有 API 有对应的 Pydantic Schema
- [ ] **注册表**: 所有新增功能已在 `REGISTRY.md` 中登记

### 3. 测试生成与执行

#### 后端测试
```bash
cd backend
# Run existing tests
pytest tests/ -v --tb=short
# Generate coverage report
pytest tests/ --cov=app --cov-report=html
```

#### 前端测试
```bash
cd frontend
npm run test
```

#### 测试用例生成指南
对于每个新实现的功能:
1. **单元测试** — Service 层的纯逻辑测试
2. **集成测试** — API 端点测试 (用 FastAPI TestClient)
3. **前端组件测试** — 关键组件的 render + interaction 测试

测试文件位置:
```
backend/tests/
├── unit/              # 单元测试
│   ├── test_llm_router.py
│   └── test_memory.py
├── integration/       # 集成测试
│   ├── test_chat_api.py
│   └── test_knowledge_api.py
└── conftest.py        # 测试 fixtures

frontend/src/
├── components/chat/__tests__/
│   └── ChatBubble.test.tsx
└── hooks/__tests__/
    └── useChat.test.ts
```

## 阶段二: 自省 (AI Code Review)

### 4. 代码审查
对本次里程碑涉及的所有变更文件进行审查，如果在前后端分离的仓库中涉及前端代码，**强烈建议引入以下专家视图**：
- **前端性能与规范自省**：调用 `@vercel-react-best-practices` 审查 React 代码性能陷阱。
- **前端 UI/UX 自省**：调用 `@web-design-guidelines` 审查页面的交互与设计合规性。

#### 审查清单
- [ ] **可读性** — 代码是否清晰易懂？命名是否准确？
- [ ] **复杂度** — 是否有过于复杂的函数？是否需要拆分？
- [ ] **错误处理** — 异常是否被正确处理？边界条件是否覆盖？
- [ ] **安全性** — 是否有注入风险？敏感数据是否暴露？
- [ ] **性能** — 是否有明显的性能瓶颈？N+1 查询？
- [ ] **复用性** — 是否有重复代码可以提取为共通函数？
- [ ] **文档** — 注释和 docstring 是否完整准确？
- [ ] **一致性** — 是否与项目整体风格一致？

### 5. 生成评审报告
创建 `docs/reviews/REVIEW-vX.Y.md`:

```markdown
# 代码评审: v{版本号}

| 字段 | 值 |
|------|------|
| **版本** | vX.Y |
| **日期** | YYYY-MM-DD |
| **涉及需求** | REQ-001, REQ-002 |
| **评审范围** | {涉及的模块} |

## 评审结果

### ✅ 通过项
- ...

### ⚠️ 建议改进
- ...

### ❌ 必须修复
- ...

## Lint 结果摘要
- ruff: {X} errors, {Y} warnings
- mypy: {X} errors
- eslint: {X} errors

## 测试结果摘要
- 后端: {X} passed, {Y} failed, {Z}% coverage
- 前端: {X} passed, {Y} failed

## 改进行动项
| # | 描述 | 优先级 | 状态 |
|---|------|--------|------|
| 1 | ... | 高 | ⬜ |
```

### 6. 更新开发日志
在 `docs/changelog/` 记录变更。

## 流程图

```
                    达到版本里程碑
                         │
              ┌──────────┴──────────┐
              │                     │
         自查 (自动)            自省 (AI)
              │                     │
    ┌─────────┼─────────┐    ┌─────┴──────┐
    │         │         │    │            │
  Lint    一致性检查  Test   代码审查   性能分析
    │         │         │    │            │
    └─────────┼─────────┘    └─────┬──────┘
              │                     │
              └──────────┬──────────┘
                         │
                    评审报告
                    REVIEW-vX.Y.md
                         │
                    修复行动项
                         │
                    更新 CHANGELOG
```
