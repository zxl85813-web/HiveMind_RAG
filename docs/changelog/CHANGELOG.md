# 📝 Changelog

## [Unreleased] — v0.1.0

### 🏗️ Foundation (2026-02-15)
- **项目初始化** — 创建整体项目结构和目录
- **后端框架** — FastAPI 应用骨架，包含 API 路由、数据模型、Schema
- **Agent 核心** — SwarmOrchestrator, SharedMemoryManager, LLMRouter, MCPManager, SkillRegistry, ExternalLearningEngine 框架
- **通信层** — WebSocket ConnectionManager, 消息协议定义
- **Skills** — 3 个 Skill 模板 (rag_search, web_search, data_analysis)
- **开发治理** — Rules, Workflows, REGISTRY.md, 文档体系
- **基础设施** — Docker Compose (PostgreSQL, Redis, ChromaDB, MinIO)

### 📋 Documented Requirements
- REQ-001: Agent 蜂巢架构
- REQ-002: 共享记忆与自省机制
- REQ-003: 对外学习机制
- REQ-004: 多 LLM 路由
- REQ-005: MCP 与 Skills 系统
- REQ-006: 混合通信 (SSE + WebSocket)
- REQ-007: 开发治理与质量体系
