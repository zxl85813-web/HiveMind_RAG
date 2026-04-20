# RAGFlow Integration Guide: Commerce Skills

本文档说明如何将 HiveMind 的“订单与物流查询”技能（Skill）和 MCP 工具集接入到 RAGFlow 产品中。

## 1. 接入原理
RAGFlow 的 Agent 插件体系支持通过 **自定义 API 工具** 或 **Python 插件** 扩展能力。HiveMind 的 MCP Server 本质上是一个遵循特定协议的标准接口，可以通过以下两种方式接入。

### 方式 A：通过 API 插件接入 (推荐)
1. **暴露 API**: HiveMind 后端通过 `/api/v1/mcp/tools` 暴露了所有已加载的工具。
2. **RAGFlow 配置**:
   - 在 RAGFlow 的【工具库】(Tools) 页面中，新增【自定义工具】。
   - 填写 HiveMind 工具的 API 地址（例如：`http://hivemind-backend:8000/api/v1/mcp/execute`）。
   - 定义参数 Schema（例如 `order_id`, `is_logged_in`）。
3. **画布配置**: 在 RAGFlow 的 Agent 画布 (Canvas) 中，拖入刚刚定义的工具节点，并与推理逻辑连线。

### 方式 B：作为 RAGFlow 本地插件 (离线集成)
若您希望将逻辑直接“嵌入”到 RAGFlow 代码库中：
1. **拷贝工具逻辑**: 将 `mcp-servers/commerce-server/server.py` 中的工具函数提取为独立的 Python class。
2. **注册到 RAGFlow**: 
   - 将该 class 放入 RAGFlow 源码的 `rag/app/agent/component/` 目录下。
   - 在 RAGFlow 的组件注册表中进行声明。

## 2. 技能意图 (Skill Intent) 的适配
HiveMind 的 `SKILL.md` 文件是为 Agent 提供的“操作指南”。在 RAGFlow 中，这些逻辑通常被转化为 **Prompt 模板**：

- **意图辨别器**: 在 RAGFlow 工作流的最前端增加一个“意图识别”节点，将 `SKILL.md` 中的“第一步：识别意图”部分内容填入该节点的 System Prompt。
- **登录状态传参**: RAGFlow 与官网前端对接时，需确保前端将 `is_logged_in` 状态写入 `Session Context` 中，这样 Agent 在调用工具时才能正确传递布尔值。

## 3. 单号识别优化
建议在 RAGFlow 的输入预处理环节增加正则校验节点（使用 REQ-028 中定义的正则表达式），可以大幅提升识别单号的准确率，避免 Token 浪费。

## 4. 多 Agent 协作与平滑切换 (PDF Page 3)
在 RAGFlow 中模拟 HiveMind 的多智体协作：
- **节点路由**: 在 Canvas 中使用一个“意图分类”节点。若识别到 `order`, `logistics`, `cancel`, `address` 关键词，路由至「电商专家」节点。
- **上下文共享**: 
  - RAGFlow 的 Session 变量应包含 `last_agent`: 记录上一次服务的 Agent 名称。
  - **切回通用 Agent**: 当「电商专家」检测到非本领域问题时（如："你们公司在哪？"），输出一个特定的 Signal（如 `[MODE: GENERAL]`），触发 RAGFlow 路由回到通用知识库节点。

## 5. 前端交互：触发登录弹窗 (PDF Page 4)
HiveMind 工具已支持返回 **UI_ACTION** 信号。
- **协议约定**: 当工具返回包含 `[UI_ACTION: TRIGGER_LOGIN_POPUP]` 的字符串时，前端监听器应捕获该信号并不展示文本，而是直接弹出官网登录对话框。
- **流程闭环**: 登录成功后，前端应刷新 `is_logged_in` 参数并自动重发最后一条查询请求。

---
## 6. 后期合并计划
当该独立功能稳定后，可以通过 HiveMind 的 `RAGGateway` 直接合并入主 RAG 流程，实现“通用问答 + 实时订单查询”的无缝切换。
