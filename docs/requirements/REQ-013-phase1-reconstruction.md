# REQ-013: HMER Phase 1 - 架构重构与性能深度调优

> **Status**: DRAFT
> **Phase**: HMER Phase 1 (Reflect & Design)
> **Baseline Reference**: [Phase 0 Status Report] (745ms TTFT, 182ms Retrieval Latency)

## 1. 业务目标
基于 Phase 0 的真实量化基线，通过架构重组（Reconstruction）解决目前阻碍系统达到“零感响应”的核心瓶颈。

## 2. 核心挑战与需求对齐
### 2.1 TTFT 瓶颈 (745ms Avg)
- **需求**: 将平均 TTFT (首字延迟) 从 745ms 压低至 **300ms** 以内。
- **现状**: 瓶颈在于 LLM 首个 Token 的生成延迟 (Network + Provider Inference)。
- **对策**: 
  - 引入 **意图探测前置 (Anticipatory Intent)**：在用户输入过程中通过流式解析预测意图。
  - **Speculative Retrieval**: 在意图概率 > 80% 时即启动后台检索。

### 2.2 P95 延时突刺 (5000ms+ Max)
- **需求**: 消除由长文档、复杂图谱搜索引起的秒级卡顿。
- **对策**: 
  - **多层级并行检索 (Tiered Parallel Retrieval)**：同步执行 Vector/Graph/Grep。
  - **流式预览 (Streaming Preview)**：检索出一部分证据即刻返回。

### 2.3 架构自愈与成本控制
- **需求**: 根据任务复杂度动态分配资源，不为简单问题消耗 Premium 模型。
- **对策**: 
  - **ClawRouter 闭环**: 自动根据 Phase 0 数据生成的“复杂度/耗时”曲线，动态路由任务。

## 3. 验收标准 (HMER Phase 1 Success Gate)
- [ ] 实验组 TTFT 均值 < 300ms。
- [ ] P95 延迟压低至 1500ms 内。
- [ ] 架构设计文档 (DES-013) 通过合规性校验。

## 4. 交付计划
1.  **S1**: 设计文档 (DES-013) - *当前正在进行*
2.  **S2**: 意图预探测层 (Intent Scaffolding) 实现。
3.  **S3**: 多路检索治理器 (Parallel Orchestrator) 实现。
