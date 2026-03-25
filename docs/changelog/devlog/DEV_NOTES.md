# 开发随记与复盘 (Development Notes & Review)

本文档用于记录我们在开发过程中遇到的**关键问题 (Issues/Bugs)** 以及**想到的好方法/架构设计 (Good Ideas/Architectural Decisions)**。
建议每次对话结束或完成一个关键里程碑后，在此处补充记录，方便后续复盘审查 (Review)。

---

## 📅 2026-03-23 (最新)

### 🌟 💡 想到的好方法 (Good Ideas)

#### 🛠 CI/E2E 架构评测常见失败与解决方案总结

在针对远程 GitHub Actions (Windows/Linux) 环境中的多种复杂失败进行深度治理后，核心经验总结如下：

1.  **性能断言与 CI 算力鸿沟 (Phase 1 Capacity)**:
    *   **问题**: 1000 条会话加载在 CI 下波动剧烈，冷启动时长飙升。
    *   **方案**: 针对 CI 环境放宽性能阈值（如从 3.5s 调整为 8.5s）。重点是检测“退化”而非绝对值，避免强制拦截。

2.  **混沌工程中的“隐形白屏” (Phase 2/3 Chaos)**:
    *   **问题**: 畸形 JSON 片段解析抛错导致组件崩溃。
    *   **方案**: 在流管理器解析器中强制 `try-catch` 隔离错误并静默处理，保证 UI 渲染韧性。并通过控制台日志同步感知 CI 崩溃点。

3.  **页面临终遥测上报 (Phase 4 Telemetry Resilience)**:
    *   **核心方案 (Double-Lock Sync)**:
        *   **同步锁**: 测试脚本显式等待 `context.waitForEvent('request')` 或 `console.log` 后再 `page.close()`，模拟“发送瞬间关闭”的极速工况。
        *   **Fetch Keepalive**: 优先使用 `fetch(..., { keepalive: true })` 上报，其在 Playwright 下的拦截稳定性优于 `navigator.sendBeacon`。
        *   **URL 归一化**: 规范 API BaseURL 处理，使用正则 `.*\/api\/v1\/...` 匹配，消除 IP/域名环境差异导致的匹配失效。

4.  **跨平台 URL 规范化**:
    *   严禁在测试拦截器中使用全路径（如 `localhost:5173`），一律改用全环境通配正则，防止 CI 环境匹配失败。
1. **弹性流管理器 (StreamManager) 与指数退避 (Exponential Backoff)**
   - **思路**：基于 `@microsoft/fetch-event-source` 构建了 `StreamManager`。关键发现在于：必须在 `onopen` 阶段对非 200/429 以外的错误主动 `throw error`，底层库才会将其判定为连接失败并触发 `onerror` 中的指数退避逻辑。
   - **价值**：显著提升了系统在极端网络抖动（如 API 限流、网关熔断）下的自我修复能力，使前端具备了“打不死”的韧性。

2. **React 状态函数式更新 (Functional State Updates) 在高频流式场景的应用**
   - **思路**：在 SSE 每秒处理数十个数据块时，传统的 `setMessages([...messages, newMsg])` 极易因为闭包捕获旧状态（Stale Closure）导致内容丢失。改为 `setMessages(prev => prev.map(...))` 后，确保了每一次追加内容都基于最实时的数据快照。
   - **价值**：彻底解决了 Playwright 自动化测试在压力测试下偶尔读到空值的随机失败问题，极大地增强了渲染的一致性。

3. **多轨流解析器的“兼容性门控” (Multi-Track Compatibility Gate)**
   - **思路**：在 `MultiTrackParser` 中通过 `(data.content ?? data.delta ?? data.message)` 这种级联回退逻辑，兼容了不同后端版本和 Mock 环境的字段差异。
   - **价值**：解耦了前后端协议的强绑定，使得前端架构在面对后端 Response Schema 微调时具备更强的鲁棒性。

### 🐞 遇到并解决的问题 (Issues Encountered)
1. **Playwright 定位符与 i18n 冲突**
   - **问题**：硬编码的 `[placeholder="输入消息"]` 在切换语言或占位符文案微调后会导致 E2E 测试全线超时失败。
   - **对策**：全面转向正则定位 `getByPlaceholder(/在这里问我|Ask me anything/i)`，不仅支持国际化，还增强了测试脚本对 UI 描述变动的容忍度。

2. **SSE 断连后的“僵尸” Loading 态**
   - **问题**：当 `fetch` 遇到严重网络错误抛出异常时，如果没有在 `catch` 块中手动派发 `error` 轨道信号，UI 组件会永远卡在 `loading` 骨架屏状态。
   - **对策**：在 `StreamManager` 的全局 `catch` 中补全了错误轨道的事件分发，确保组件能在任何灾难性连接失败后优雅停止 Loading 并展示错误提示。

---

## 📅 2026-02-23

### 🌟 💡 想到的好方法 (Good Ideas)
1. **评估与微调的数据闭环 (RAGas + SFT Data Loop)**
   - **思路**：在实现 RAG 评估时，不仅仅停留在“打分”层面，而是让低分回答转化为真实的资产。我们在 `EvalPage` 中添加了“标记为 Bad Case”和“转为微调指令”的闭环，直接将错误上下文和人工修正后的答案存入 `FineTuningItem` 数据集中。
   - **价值**：极大降低了后续监督微调（SFT）构建高质量数据集的成本，形成“使用越久 -> Bad Case 暴露越多 -> 修正微调库越大 -> 模型越精准”的飞轮效应。

2. **前端拦截器与 Mock 无缝切换**
   - **思路**：通过 MSW (Mock Service Worker) 和 `run_mock.bat` 脚本，将前后端联调解耦。在尚未部署或启动耗资源大模型的情况下，前端依然可以完成完整业务链路 UI 的开发和验证。

3. **父子分块 (Parent-Child Chunking) 与检索扩展**
   - **思路**：在向 Vector DB 写入文本时，只把短小精悍的 child chunk （例如 200字，不包含 `is_parent: True` 标签的切片）拿去做 Embedding，而在它身上挂载 `parent_chunk_id`。检索后在 `ParentChunkExpansionStep` 里通过 ID 反向去 SQL DB 查出大块的 1000字 content 进行替换。并配上了基于 Zhipu/GPT 的查询改写与 HyDE（假设性文档）构建。
   - **价值**：既保证了向量检索能够精准踩中关键词 (Child)，又保证了喂给 LLM 的上下文语境充足且连续 (Parent)，大幅缓解了长尾截断和幻觉问题。

4. **防提示词注入 (Prompt Injection) 与越狱控制**
   - **思路**：在 Prompt 引擎层（`base/system.yaml`, `supervisor.yaml`），增加了严厉且具体的防御性系统提示。比如遇到 "Forget all previous rules" 或要求切换为 "developer mode"，强行干预路由分配或返回拦截。此外依靠后端流式生成的 Outbound 脱敏（M2.2.6 已实现），形成了“输入防越狱 + 输出防泄露”的双重保障。
   - **价值**：保护多 Agent 的核心系统提示词不被恶意套取，强化了企业级 RAG 的合规底线。

5. **MCP 与 Skills 的元架构融合 (MCP & Meta-Skills)**
   - **思路**：接入 MCP (Model Context Protocol) 意味着 Agent 系统可以无限地挂载操作系统级别的能力（本地文件、IDE、数据库）。然而，单有 MCP 接口还不够，我们为它配备了 `SkillRegistry` 的动态技能体系，并且设计了元技能（Meta-Skill：如 `mcp-builder` 和 `skill-creator`），使系统可以在运行时生成新的技能样板代码，自建并热加载新的人机协同工具。
   - **价值**：MCP 提供了硬件/服务连接层，Skills 提供了逻辑/封装层。这种解耦加元编程的设计使得 Agent 可以逐步实现自我迭代升级，也就是真正意义上的持续演进能力。

6. **基于 LangGraph 的纯异步批处理引擎 (Batch Engine & DAG)**
   - **思路**：为弥补闲置算力的利用率和流式交互不能长时间无人值守的缺陷，引入了基于有向无环图 (DAG) 的 `JobManager`。它拥有一个 `Scheduler Node` 和一个并行调度的 `Worker Node`。
   - **价值**：系统不仅能在前台和用户打字，现在可以在后台同时接收含有 N 个具有前后置依赖 (Depends_on) 的任务（提取、分析、生成），并自动调度、执行、容错、持久化 (Pickle/Sqlite)。这补齐了系统的最后一环：**离线与大规模任务的吞吐能力**。
### 🐞 遇到并解决的问题 (Issues Encountered)
1. **Pyre2 类型提示丢失 / Lints**
   - **问题**：IDE 经常报 `Could not find import`，主要因为某些动态导入或 SQLAlchemy/SQLModel 的复杂类型推导没有被静态分析识别。
   - **对策**：不影响实际运行。后续可以通过更严格的 `__all__` 导出或添加类型桩文件 (stubs) 来缓解。

2. **前端状态更新延迟**
   - **问题**：在部分长列表或流式对话 (SSE) 场景下，React 频繁 `setState` 会导致打字机效果卡顿。
   - **对策**：在 `ChatPanel` 等组件中合理抽取子组件，或使用 `useRef` 配合定期批量更新 DOM 来提升渲染性能。

---

## 📅 以往核心记录回顾

### 🌟 💡 架构亮点
1. **AI-First 的组件设计与 Action System**
   - 直接让 LLM 在回复中携带结构化的 `AIAction` (`navigate`, `execute` 等)，极大地提升了系统操作效率。前端解析这些 Action 并渲染成实际的按钮组合。
2. **多租户与 RBAC (基于角色的权限) 预留**
   - 设计之初就充分考虑了权限上下文，目前的路由、Audit (审核) 机制天然支持扩展多人使用环境下的交叉认证。

### 🐞 绕过的坑
- **文档分块内存爆炸**：最初全量读入 PDF/Word 时，长文本 OOM。引入流式解析并在 Pipeline 阶段引入限流后得到解决。
- **端口冲突**：之前 `uvicorn` 默认起在 `0.0.0.0` 导致 Windows 报 `WinError 10013` (常被 Hyper-V 或者系统代理保留)，改为显式指定 `127.0.0.1:8000` 后彻底解决。

---
> **后续流程规范**：每次我们讨论完新的模块结构或解决复杂 Bug 时，请提醒我更新此文档！
