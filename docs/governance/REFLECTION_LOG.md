# 🕯️ HiveMind 工程反思与最佳实践图谱 (Reflection Log)

> **"不畏回归，不惮反思。"** — 本文件记录了开发过程中遇到的重大故障、底层隐坑及架构治理的深刻教训。每次开发迭代结束前需回顾此文件，防止同一类错误在 HiveMind 智体群体中再次蔓延。

---

## 🛑 故障与反思 (Post-Mortem Library)

### [2026-04-07] RAG 性能战役：语法、路径与依赖的多重崩塌
*   **故障点 1：f-string 语法解析冲突**
    *   **现象**：Prompt 中包含 JSON 示例 `{}`，导致 Python 执行 `f-string` 格式化时报错 `ValueError`，Pipeline 跌入 fallback 返回 `None`。
    *   **反思**：长文本 Prompt 定义严禁使用原始 `f-string` 直接包裹复杂 JSON，必须对 `{}` 进行双写转义（`{{` / `}}`）。
    *   **改进**：后续所有 Prompt 统一使用 `jinja2` 模板或独立文本加载，从根源规避转义问题。

*   **故障点 2：VFS (虚拟文件系统) 指向偏差**
    *   **现象**：`Broker` 机制虽然优雅，但在高并发评测中导致 `viking://` 路径读取 `Match: False`，生成结果在链路中“失踪”。
    *   **反思**：**方便是架构的毒药**。核心生成链路（Generation Chain）不应过度依赖这种黑盒订阅/分发，应回归 **内存直连 (Direct-Memory)** 以提升确定性。
    *   **改进**：已修改 `GenerationContext`，将检索内容与生成草稿转为内存持久化字段。

*   **故障点 3：库的黑盒默认行为 (onnxruntime 依赖僵局)**
    *   **现象**：ChromaDB/LangChain 在环境缺少 `onnxruntime` 时偷偷回退到受损状态或报错，导致语义检索层彻底失效，用户却感知不到（只觉得分数低）。
    *   **反思**：**严禁向第三方库传递原始文本 (Raw Text)**。所有的向量预处理必须在受控的 `EmbeddingService` 中显式执行。
    *   **改进**：已实施 **ARAG-003 远程向量透传策略**，强称在调用 Chroma 之前注入远程向量，绕过本地推理劫持。

### [2026-04-13] 系统互联与权限孤岛：IPv6 陷阱与状态滞后
*   **故障点 1：环境解析歧义 (localhost vs 127.0.0.1)**
    *   **现象**：后端监听 `127.0.0.1`，但前端代理或浏览器在 Windows 下将 `localhost` 解析为 IPv6 的 `::1`，导致连接被拒 (`ERR_CONNECTION_REFUSED`)。
    *   **反思**：**配置的模糊性是稳定性的敌人**。在混合使用 IPv4/IPv6 的现代 OS 中，绝对禁止在代理配置中使用 `localhost`，必须明确指定 IP 协议栈。
    *   **改进**：全量修改 `vite.config.ts` 代理目标为 `127.0.0.1`；后端启动脚本强制绑定 `0.0.0.0` 以兼顾多网卡环境。
*   **故障点 2：异步状态的“权限空窗期”**
    *   **现象**：登录成功与 Profile 获取是分离的异步过程，导致用户在跳转瞬间看到的是权限受限的旧 UI，产生“菜单丢失”的假象。
    *   **反思**：**关键状态必须原子化 (Atomic State Sync)**。不应依赖跳转后的二次请求来确定初始权限。
    *   **改进**：重构登录接口，实现 **“登录即 Profile”** 的原子握手；增加 `AccessGuard` 的状态订阅，消灭权限判定死区。
*   **故障点 3：React 属性强力污染 (Prop Pollution)**
    *   **现象**：组件误传非法属性（如 `block`）触发 React 运行时警告。
    *   **反思**：这是由于对第三方库（Ant Design）API 的“经验性猜测”而非“类型化检查”导致的。
    *   **改进**：强制在 IDE 中启用严格类型推导，严禁使用 `any` 绕过 UI 组件的 Props 检查。

---

## 🛠️ 系统性补全方案 (Advanced Hardening Matrix - Updated)

### 策略 D：状态原子化保障 —— “登录握手协议” (Atomic Auth Handshake)
*   **工程标准**：
    *   **Immediate Injection**：登录接口返回体必须包含用户的核心 Role 与 Permission 列表。
    *   **Auth Store Guard**：`setAuthenticated` 必须同时接收并注入用户详情，阻塞导航直到 Profile 状态机完成首记映射。
    *   **Navigation Reactivity**：侧边栏菜单生成函数必须强依赖于 `profile` 实例，确保状态变更时 UI 实时重新计算。

---

## 🛑 故障与反思 (Post-Mortem Library - Continued)

### [2026-04-08] 专项治理：Nginx 接口短路与前端视觉变形
*   **故障现象**：在快速刷新或并发请求时，Nginx 返回 `200 OK` 但正文为空（Interface Short-circuit），导致前端 React/antd 组件由于数据骤降导致容器高度坍塌，CSS 动画由于失去布局支撑而发生严重的扭曲/闪烁（Layout Thrashing）。
*   **深度反思**：
    1.  **Nginx 默认缓冲陷阱**：默认的 `proxy_buffering` 在客户端提前断开（Refresh）时可能产生残片污染。
    2.  **动画与生命周期脱钩**：CSS 动画在合成层异步运行，而数据更新在主线程同步发生。当“空数据”瞬间到达时，动画没有收到“暂停”或“维持布局”的指令，导致容器瞬间缩回（变形）。
    3.  **缺乏请求序校验**：前端盲目接受所有到达的响应，没有区分“过期响应”与“当前有效响应”。

---

## 🕳️ 已知隐坑与待办检查 (Arch-Level Risks)

### 1. 存储层：ChromaDB 句柄泄露
*   **风险**：在 FastAPI 异步环境下重复创建 `PersistentClient` 必然导致 `database is locked`。
*   **守卫建议**：必须全局单例化 Chroma Client，并在进程关闭时显式执行 `client.heartbeat()` 检查，确保连接池健康。

### 2. 检索层：混合搜索权重失衡
*   **风险**：ES 的 BM25 分（高量纲）与 Vector 的 Cosine 分（[0, 1] 区间）直接相加会导致语义价值被稀释。
*   **守卫建议**：引入 RRF (Reciprocal Rank Fusion) 归一化算法，或在合并前强制对两类得分进行区间缩放。

### 3. 通信层：Nginx 接口短路与时序竞争
*   **风险**：Nginx 反向代理在负载瞬时波动时可能返回 `200 OK` 但数据包体不完整或为空。
*   **守卫建议**：
    *   **前端**：引入 **“静默重试机制” (Retrace)**，对非预期空数据进行指数退避重连。
    *   **后端**：在 API 响应头中注入 `X-Response-Sequence`，前端根据序列号校验数据时序的“新鲜度”。

---

## 🛠️ 系统性补全方案 (Advanced Hardening Matrix)

为彻底解决 RAG 回答空洞、接口短路与视觉跳动，HiveMind 后续开发必须严格执行以下 **“三位一体”策略矩阵**：

### 策略 A：后端代理层 —— “防抖与缓冲加固” (Nginx Hardening)
*   **强制配置项**：
    *   `proxy_ignore_client_abort on;` —— 确保后端 API 完整执行，防止连接被浏览器刷新强行掐断产生残片。
    *   `proxy_buffer_size 128k;` / `proxy_buffers 4 256k;` —— 扩充缓冲区，防止大数据量（如长 RAG 响应）被切断导致 200 空包。
    *   `proxy_http_version 1.1;` + `proxy_set_header Connection "";` —— 启用高版本 Keepalive，防止旧连接残留 Buffer 污染新请求。

### 策略 B：前端逻辑层 —— “时序幂等控制” (Sequence Control)
*   **工程标准**：
    *   **Request ID & Sequence**：每一个 API 调用必须附带一个递增的序列号（或随机 ID）。
    *   **Timestamp Fencing**：前端状态机更新前必须校验响应的 `Timestamp`。严禁“旧的空响应”覆盖“新的有效状态”。
    *   **Exponential Backoff Retrace**：若接口返回非预期空值（`[]`），前端触发 **“静默重播 (Retrace)”** 机制（重连 3 次，间隔 100ms/300ms/1000ms），给上游服务同步/热热的机会。

### 策略 C：前端渲染层 —— “布局生命周期锁定” (Layout Locking)
*   **视觉规范**：
    *   **antd.Skeleton & Min-Height**：列表或内容容器必须显式定义 `min-height`（推荐 200px 以上）。在 `Loading` 或 `Retrace` 阶段，antd 骨架屏必须保持活跃，严防容器坍塌（Collapse）。
    *   **Animation Lifecycle Sync**：使用 CSS 变量（如 `--anim-state: paused|running`）锚定数据加载状态。
    *   **Double-Buffering Check**：数据从“为空”到“有值”的更新必须在 `requestAnimationFrame` 中同步执行，确保 DOM 重拍与动画起始点对齐，消除闪动感。

---

## 🛠️ 核心开发原则 (Golden Rules - Updated)

1.  **NO MAGIC & NO GUESS**：拒绝库的默认行为，亦拒绝凭经验猜测组件 Props。
2.  **DIRECT ACCESS**：内存直连优先。
3.  **STRICT RETRY & SEQUENCING**：外部 API 必须受控重试且按序接受。
4.  **UI STABILITY FIRST**：宁可显示骨架屏，绝不允许布局坍塌。
5.  **ATOMIC OVER ASYNC**：核心状态（认证、权限、拓扑）必须在关键跳转前完成原子握手。
6.  **ENV EXPLICITNESS**：配置文件中严禁使用 `localhost`，必须显式指定 `127.0.0.1` 或 `0.0.0.0`。
7.  **EVAL-DRIVEN**：分数下降即代码违约。

---

*最后更新日期: 2026-04-13*
