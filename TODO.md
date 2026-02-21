# 📋 HiveMind RAG — TODO & Discussion Backlog

> 记录所有待讨论和待实现的功能点。状态标记：
> - ⬜ 待讨论
> - 🟡 讨论中
> - 🟢 方案已定
> - ✅ 已实现
> - 🔴 已废弃

---

## 1. 🐝 Agent 蜂巢架构 (Agent Swarm / Hive)

- ⬜ **1.1 Supervisor 模式设计** — Supervisor Agent 的路由策略、降级机制
- ⬜ **1.2 Agent 注册与发现** — 动态注册新 Agent，热插拔能力
- ⬜ **1.3 Agent 间通信协议** — Agent 之间的消息传递格式和协作方式
- ⬜ **1.4 Agent 生命周期管理** — 创建、运行、暂停、销毁
- ⬜ **1.5 并发与负载** — 多 Agent 并行执行的调度策略
- ⬜ **1.6 Agent 执行可视化** — 前端展示 Agent 协作过程的 DAG 图

---

## 2. 🧠 共享记忆与自省机制 (Shared Memory & Reflection)

- ⬜ **2.1 共享记忆存储设计** — 短期记忆 (会话级) vs 长期记忆 (持久化) 的存储方案
- ⬜ **2.2 记忆索引与检索** — 如何高效检索相关记忆（向量检索 / 关键词 / 时序）
- ⬜ **2.3 Agent TODO List** — Agent 集群共享的待办事项队列
  - ⬜ 自动从对话中提取 TODO
  - ⬜ Agent 间的任务分配与认领
  - ⬜ TODO 优先级与截止时间管理
- ⬜ **2.4 自省 (Reflection) 流程**
  - ⬜ 回答质量自评机制（Agent 评估自己的输出）
  - ⬜ 错误检测与自纠正（发现矛盾或错误时自动修正）
  - ⬜ 周期性回顾（定期回顾历史记忆，提炼知识）
- ⬜ **2.5 用户介入提醒** — 当 Agent 信心不足或遇到歧义时，主动通知用户介入
- ⬜ **2.6 记忆衰减策略** — 旧记忆的权重衰减与清理机制

---

## 3. 🌐 对外学习机制 (External Learning & Subscription)

- ⬜ **3.1 技术动态订阅引擎**
  - ⬜ 基于当前技术栈自动生成监控关键词
  - ⬜ 定时爬取 / API 获取技术资讯（GitHub Trending, Hacker News, ArXiv 等）
  - ⬜ 新技术相关性评估（与当前架构的匹配度打分）
- ⬜ **3.2 开源项目发现与推荐**
- ⬜ **3.3 Skill 市场 / 技能发现**
- ⬜ **3.4 学习成果反馈** — WebSocket 推送通知机制

---

## 4. 🔧 MCP (Model Context Protocol) 集成

- ⬜ **4.1 MCP Client 核心实现** — 在 Agent Runtime 中集成 MCP Client
- ⬜ **4.2 MCP Server 注册中心** — 管理多个 MCP Server 的连接与发现
- ⬜ **4.3 内置 MCP Servers** — Database / Filesystem / API Gateway
- ⬜ **4.4 自定义 MCP Server 脚手架**
- ⬜ **4.5 MCP Tools ↔ LangChain Tools 适配**

---

## 5. 🧩 Skills 系统

- ⬜ **5.1 Skill 规范定义** — SKILL.md 格式、目录结构规范
- ⬜ **5.2 Skill 加载器** — 动态加载与卸载 Skills
- ⬜ **5.3 Skill 注册中心** — 注册、发现、版本管理
- ⬜ **5.4 内置 Skills** — RAG / 文档摘要 / 数据分析 / 代码生成 / 搜索
- ⬜ **5.5 Skill 权限与安全** — Skill 的沙箱执行环境

---

## 6. 🔀 多 LLM 路由

- ⬜ **6.1 LLM Provider 抽象层** — 统一接口对接多家 LLM
- ⬜ **6.2 路由策略引擎** — 按任务类型/成本/延迟/Fallback
- ⬜ **6.3 模型性能监控** — 响应时间、成功率、成本统计
- ⬜ **6.4 支持的模型列表** — 确定首批支持的 LLM 列表

---

## 7. 📡 通信层 (SSE + WebSocket)

- ⬜ **7.1 SSE 流式输出协议** — 事件类型定义、错误处理、重连
- ⬜ **7.2 WebSocket 消息协议** — 类型枚举、JSON Schema、心跳重连
- ⬜ **7.3 前端通信 Hooks** — useSSE, useWebSocket

---

## 8. 📚 RAG 核心

- ⬜ **8.1 文档处理 Pipeline** — 上传 → 解析 → 分块 → 向量化 → 索引
- ⬜ **8.2 检索策略** — 向量检索、关键词检索、混合检索
- ⬜ **8.3 Reranker** — 二次排序模型选择
- ⬜ **8.4 知识库管理** — CRUD、权限、元数据
- ⬜ **8.5 引用溯源** — 回答中标注来源文档

---

## 9. 🎨 前端

- ✅ **9.1 设计系统** — Cyber-Refined 主题、色彩、组件规范
- ✅ **9.2 AI-First 布局** — 顶部导航 + 内容区 + 永驻 Chat Panel
- ✅ **9.3 页面规划**
  - ✅ Dashboard 概览首页
  - ✅ 知识库管理 (占位)
  - ✅ Agent 监控 (基础)
  - ✅ 系统设置 (基础)
  - ✅ 技术动态 (占位)
- ✅ **9.4 AI 交互组件** — ChatPanel + ActionButton + 上下文感知
- ⬜ **9.5 Agent 协作可视化** — 实时展示 Agent 执行过程 DAG

---

## 10. 🏗️ 基础设施

- ✅ **10.1 认证模块 (security.py)** — JWT + 密码哈希 (已实现框架)
- ⬜ **10.2 数据库选型确认** — PostgreSQL + 向量数据库
- 🟢 **10.3 Docker Compose** — docker-compose.dev.yml 已有基础
- ⬜ **10.4 CI/CD** — 自动化构建与部署
- ⬜ **10.5 可观测性** — LangFuse / 日志 / 监控
- ⬜ **10.6 API 文档** — OpenAPI / Swagger 规范

---

## 11. 🔒 安全

- ⬜ **11.1 Prompt 注入防护**
- ⬜ **11.2 敏感数据脱敏**
- ⬜ **11.3 API 限流**
- ⬜ **11.4 Agent 执行沙箱**

---

## 12. 🤖 AI 开发治理 (已建立)

- ✅ **12.1 功能注册表** — REGISTRY.md (开发前必查)
- ✅ **12.2 编码规范** — .agent/rules/coding-standards.md
- ✅ **12.3 设计系统规范** — .agent/rules/frontend-design-system.md
- ✅ **12.4 项目结构约束** — .agent/rules/project-structure.md
- ✅ **12.5 标准开发流程** — 6 个 workflow (见下表)
- ✅ **12.6 需求文档管理** — 7 个 REQ 文档已归档
- ✅ **12.7 架构设计文档** — docs/architecture.md + design/

---

> 📅 Last Updated: 2026-02-15
> 💡 使用方法：每次讨论后更新对应项的状态标记
