---
description: 为新功能或组件编写自动化测试的标准流程
---

# 🧪 编写与执行测试工作流 (Write Tests)

> **触发时机**: 在完成某个后端 Service/Route 或前端组件后，提交 PR 前必须执行此流程。
> **前置阅读**: [`.agent/rules/testing_guidelines.md`](../rules/testing_guidelines.md)

## 📋 执行步骤

### Step 1: 确定测试层次与视图
根据你刚才写的代码性质：
- 纯逻辑 / 工具库 -> 写 **Unit Test**。
- API Endpoint -> 必须写 **Integration Test**。
- UI 组件带复杂交互 -> 写 **Component Test**。

确保你的测试涵盖了【设计契约视角】(正常走得通) 和【代码例外视角】(出错了也能防得住)。

### Step 2: 定位并创建测试文件
- **后端**: 按源码路径在 `backend/tests/` 内创建对应的文件。
  例如：`backend/app/api/routes/knowledge.py` -> `backend/tests/integration/api/test_knowledge.py`。
- **前端**: 在组件旁边创建。
  例如：`frontend/src/components/chat/ChatBubble.tsx` -> `frontend/src/components/chat/ChatBubble.test.tsx`。

### Step 3: 使用固件 (Fixtures) 与 Setup
- 不要直接在测试函数里 hardcode 配置数据库！在后端的 `conftest.py` 寻找已有的 `db_session`, `test_client`, `mock_user` 固件。
- 在前端，寻找全局包裹了 Theme 和 i18n 的渲染函数如 `renderWithProviders(<ChatBubble />)`。

### Step 4: 编写断言 (Assert)
在执行完目标函数后，做三件事判断：
1. **状态断言**: HTTP Status 正常吗？`response.status_code == 200`
2. **数据契约断言**: JSON 包裹了 ApiResponse 吗？`assert data["success"] is True`
3. **副作用断言**: 你如果调了"清空操作"，数据库真的空了吗？查询一遍确认。

### Step 5: 运行并验证覆盖率
// turbo
```bash
cd backend
pytest tests/ --cov=app --cov-fail-under=80
```
或对于前端：
```bash
cd frontend
npm run test:unit
```

### Step 6: 修复并上报
如果你的测试没法跑（比如被框架版本限制、Mock 掉进了死胡同），不要搁置，一定要去项目的 `TODO.md` 写明：
`- [ ] 🛑 BLOCKED: Test creation failed for <组件名> - Reason: <依赖无法注入, etc>` 
