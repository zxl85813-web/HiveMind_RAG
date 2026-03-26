# 📋 HiveMind Intelligence Swarm — 开发 TODO 清单

> **⚠️ 强制规则**: 每次开发对话结束前，必须更新此文件。
> 任何"先不做"、"暂时跳过"、"以后再说"的内容必须记录在此。
>
> 🗺️ **完整开发计划**: [docs/ROADMAP.md](docs/ROADMAP.md) — 7 个里程碑 / 87 个任务 / ~30 天   
> 📄 **需求文档**: `docs/requirements/`
> 🛡️ **架构治理**: [开发治理准则](docs/DEV_GOVERNANCE.md)
> 📦 **功能注册表**: [REGISTRY.md](REGISTRY.md)
> 🕒 **历史归档**: [docs/changelog/devlog/](docs/changelog/devlog/)

---

## 🚦 任务看板

| 维度 | Agent / 模块 | 核心待办 (Now / Next / Later) | 状态 |
| :--- | :--- | :--- | :--- |
| **路由层** | RAGGateway | ⬜ 检索策略 A/B 测试基线 | 🟡 |
| **执行层** | Workers | ⬜ 标签→Pipeline 动态分派系统 | ⬜ |
| **存储层** | Memory Agent | ⬜ 知识库 Gap-Insight 自动诊断 | ⬜ |
| **治理层** | Governance Agent | ⬜ 自动审核规则引擎联调 | ⬜ |

---

## 🛠️ 当前活跃任务 (Active)

### [2026-03-26] 全方位的可观测性治理 (Unified Observability Promotion)

- [x] **基建验证**: 成功落地 `UnifiedLog` 强契约协议，单测 7/7 通过
- [x] **业务重构**: 完成 `ChatPage` 与 `KnowledgePage` 的“样板房”式重构
- [x] **安全封印**: `post-build.js` 自动隔离 SourceMap，本地 `debug_symbols` 归档
- [x] **调试利器**: 交付 `trace_analyzer.py` 并通过了 `drill-trace-999` 实战演推
- [x] **标准确立**: 发布 [Unified Observability Standard](docs/architecture/unified_observability_standard.md)

### [2026-03-25] 文档系统对齐与架构治理 (Docs Transition to SSoT)

- [x] **SSoT 对齐**: 彻底清理并重建全站文档索引 (Index/README.md)
- [x] **前端核心层定义**: 在 DES-001 中补齐 `src/core` (Monitor, Intent, LocalEdge)
- [x] **治理规范确立**: 发布 GOV-001，定义 RDD 与 Phase Gate 审计规范
- [x] **后端架构大一统**: 整合碎片化设计，发布 [DES-003](docs/design/DES-003-BACKEND_ARCHITECTURE.md)
- [x] **AI UX 表达**: 发布 [AI_FRONTEND_STRATEGY](AI_FRONTEND_STRATEGY.md) 面向 AI 场景的技术白皮书
- [x] **运维对齐**: 整合 `backend/scripts/` 监控，接入 `UnifiedLog` 协议 (P0 级已完成)

### 🎯 下一阶段核心任务 (Phase 4.1+)

- [x] **后端预感应支持**: 为 retrieval 接口实现 `is_prefetch` 参数，开启“轻量级预热”
- [x] **前端预测增强**: 在 IntentManager 中集成 AI Warmup 探测器
- [ ] **HMER 自动化评分**: 开发 `scripts/check_registration_coverage.py` 自动计算 REGISTRY.md 对齐度
- [ ] **断点续传联调**: 验证 `StreamManager` 与后端 `_resume_index` 协议的端到端闭环
- [ ] **GitHub Issues 迁移**: 将本 TODO.md 的活跃项迁移至 GitHub Projects

### [2026-03-24] 卫星对账与遥测加固 (Phase 4 Telemetry Hardening)

- ✅ Fix: StreamManager TTFT 字符串匹配正则化 (兼容空格差异)
- ✅ Feature: MonitorService 离屏补发机制 (keepalive + fallback sendBeacon)
- ✅ Backend: 实现 /api/v1/telemetry 遥测收口端点
- ✅ DevOps: 配置 LLM_BASE_URL 动态注入

---

## 🐛 待修复 Bug / 风险追踪

- [ ] **BUG-001**: 某些文档在 `view_file` 时被识别为 `unsupported mime type` (由于异常 UTF-8 字节)
- [ ] **RISK-001**: 并发开发时 TODO.md 的合并冲突风险 (建议转向 GitHub Issues)
