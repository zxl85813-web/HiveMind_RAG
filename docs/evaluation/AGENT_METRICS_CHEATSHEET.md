# 🤖 Agent 评测指标速查表

> 快速参考卡片，用于日常 Agent 评测和问题诊断

---

## 一、指标一览表

### 核心能力指标

| 指标 | 中文名 | 评估层级 | 健康阈值 | 权重 |
|-----|-------|---------|---------|-----|
| `task_completion` | 任务完成度 | L3 | ≥ 0.85 | 40% |
| `reasoning_quality` | 推理质量 | L3/L4 | ≥ 0.80 | 25% |
| `tool_accuracy` | 工具准确性 | L1 | ≥ 0.90 | 20% |
| `safety_score` | 安全合规 | L1/L3 | ≥ 0.95 | 15% |

### 协作指标 (L2)

| 指标 | 公式/定义 | 健康阈值 |
|-----|---------|---------|
| `routing_accuracy` | 路由正确数 / 总路由数 | ≥ 0.85 |
| `handoff_quality` | 上下文完整性评分 | ≥ 0.80 |
| `parallel_efficiency` | 并行耗时 / 串行耗时 | ≤ 0.6 |
| `consensus_quality` | 多 Agent 输出一致性 | ≥ 0.75 |

### 过程完整性指标 (L4)

| 指标 | 检查内容 | 健康阈值 |
|-----|---------|---------|
| `evidence_lineage` | 结论是否有证据支撑 | ≥ 0.85 |
| `critical_friction` | 审查是否有实质性质疑 | ≥ 0.70 |
| `truthfulness` | 步骤间逻辑一致性 | ≥ 0.90 |
| `compliance` | 系统指令遵从度 | ≥ 0.95 |

---

## 二、快速诊断流程图

```
                    ┌─────────────────┐
                    │  E2E 得分 < 0.7  │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ routing_accuracy│ │ tool_accuracy   │ │ reasoning_quality│
│     < 0.8       │ │     < 0.85      │ │     < 0.75       │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  路由问题        │ │  工具问题        │ │  推理问题        │
│  - Supervisor   │ │  - Tool Schema  │ │  - Prompt       │
│  - Vector Index │ │  - API 稳定性   │ │  - 基座模型      │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## 三、常见问题速查

### 问题 1: 路由准确率低 (Routing Accuracy < 0.8)

**症状**: 请求被分配给错误的 Agent

**可能原因**:
- [ ] Supervisor Prompt 描述不清晰
- [ ] Agent 能力描述重叠
- [ ] 向量路由索引过时

**快速修复**:
```python
# 1. 优化 Agent 描述
agent_def = AgentDefinition(
    name="code_agent",
    description="专门处理代码审查、漏洞检测、代码生成任务。不处理文档查询。",
    # 明确边界 ↑
)

# 2. 刷新向量路由索引
await vector_agent_router.rebuild_index()

# 3. 检查 JIT 路由缓存
await CacheService.clear_route_cache()
```

### 问题 2: 工具调用失败率高 (Tool Error Rate > 0.1)

**症状**: Agent 频繁调用工具失败

**可能原因**:
- [ ] 工具 Schema 定义不准确
- [ ] 参数构造错误
- [ ] 外部服务不稳定

**快速修复**:
```python
# 1. 检查工具 Schema
tool_schema = {
    "name": "search_documents",
    "description": "搜索知识库文档。必须提供 query 参数。",
    "parameters": {
        "type": "object",
        "required": ["query"],  # 明确必填参数
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
            "top_k": {"type": "integer", "default": 5}
        }
    }
}

# 2. 添加工具调用重试
@retry(max_attempts=3, backoff=exponential)
async def invoke_tool(tool_name, params):
    ...
```

### 问题 3: 反思循环过多 (Reflection Count > 3)

**症状**: Agent 反复修改输出，无法收敛

**可能原因**:
- [ ] 评估标准过于严格
- [ ] Agent 输出质量不稳定
- [ ] 评估器与 Agent 风格不匹配

**快速修复**:
```python
# 1. 调整评估阈值
PASS_THRESHOLD = 0.65  # 从 0.7 降低到 0.65

# 2. 增加反思上限保护
if reflection_count > 3:
    logger.warning("Too many reflections, forcing FINISH")
    return {"next_step": "FINISH"}

# 3. 检查评估器偏差
# 确保评估器和 Agent 使用相同的输出风格指南
```

### 问题 4: L4 审计失败 (INTEGRITY_FAIL)

**症状**: 过程完整性审计不通过

**可能原因**:
- [ ] 结论缺乏证据支撑 (Magic Conclusions)
- [ ] 审查流于形式 (Rubber Stamp)
- [ ] 步骤间逻辑矛盾

**快速修复**:
```python
# 1. 强化证据引用要求
prompt = """
每个结论必须引用具体的证据来源：
- 引用检索文档: [DOC-1], [DOC-2]
- 引用前序步骤: [STEP-1], [STEP-2]
不允许无来源的结论。
"""

# 2. 增强 Reviewer 批判性
reviewer_prompt = """
你是一个严格的审查者。你必须：
1. 找出至少一个潜在问题
2. 提出至少一个改进建议
不允许简单地说"看起来不错"。
"""
```

---

## 四、阈值参考表

### 生产环境建议阈值

| 场景 | 任务完成 | 推理质量 | 安全合规 | 说明 |
|-----|---------|---------|---------|-----|
| **通用助手** | 0.75 | 0.70 | 0.90 | 容错度较高 |
| **代码审查** | 0.85 | 0.85 | 0.95 | 准确性优先 |
| **安全审计** | 0.90 | 0.90 | 0.99 | 零容忍错误 |
| **创意写作** | 0.60 | 0.60 | 0.85 | 允许发散 |

### CI/CD 门禁建议

```yaml
quality_gates:
  blocking:  # 必须通过
    - safety_score >= 0.90
    - tool_accuracy >= 0.85
  warning:   # 警告但不阻塞
    - task_completion >= 0.70
    - reasoning_quality >= 0.65
```

---

## 五、评测命令速查

```bash
# L1: 单 Agent 测试
python -m pytest tests/agents/test_code_agent.py -v

# L2: 协作测试
python -m pytest tests/agents/test_swarm_routing.py -v

# L3: 能力评测
python backend/scripts/l3_dashboard_sync.py --threshold 0.7

# L4: 过程审计
python backend/scripts/gate_l4_process_integrity.py

# 完整评测流水线
python -m scripts.agent_eval run --all-levels

# 对抗性测试
python -m scripts.agent_eval adversarial --category injection
```

---

## 六、监控告警规则

```python
ALERT_RULES = {
    "agent_quality_low": {
        "condition": "avg(quality_score) < 0.6 for 10m",
        "severity": "critical",
        "action": "检查 Prompt 和模型状态"
    },
    "routing_degradation": {
        "condition": "routing_accuracy < 0.75 for 5m",
        "severity": "warning",
        "action": "检查 Supervisor 和向量索引"
    },
    "reflection_loop": {
        "condition": "avg(reflection_count) > 3 for 5m",
        "severity": "warning",
        "action": "检查评估阈值和 Agent 输出"
    },
    "tool_failure_spike": {
        "condition": "tool_error_rate > 0.15 for 3m",
        "severity": "critical",
        "action": "检查工具服务和 Schema"
    },
    "l4_integrity_fail": {
        "condition": "l4_verdict == 'INTEGRITY_FAIL'",
        "severity": "critical",
        "action": "人工审核推理链"
    }
}
```

---

## 七、L4 审计结果解读

### Verdict 类型

| Verdict | 含义 | 后续动作 |
|---------|------|---------|
| `INTEGRITY_PASS` | 过程完整，结论可信 | 无需干预 |
| `INTEGRITY_FAIL` | 过程有严重缺陷 | 标记为 REJECTED，人工复核 |
| `DANGEROUS_LUCK` | 结果正确但过程有问题 | 记录并改进流程 |

### 常见 Findings

| Finding | 含义 | 改进方向 |
|---------|------|---------|
| `MAGIC_CONCLUSION` | 结论无证据支撑 | 强化证据引用 |
| `RUBBER_STAMP` | 审查流于形式 | 增强 Reviewer 批判性 |
| `PROCESS_POLLUTION` | 引入大量无关信息 | 优化上下文过滤 |
| `COGNITIVE_DISHONESTY` | 声称遵守但实际违反 | 加强指令遵从检查 |

---

## 八、BadCase 分类标签

| 标签 | 说明 | 优先级 |
|-----|------|-------|
| `hallucination` | 幻觉/编造信息 | P0 |
| `tool_misuse` | 工具使用错误 | P0 |
| `safety_violation` | 安全违规 | P0 |
| `routing_error` | 路由错误 | P1 |
| `incomplete_reasoning` | 推理不完整 | P1 |
| `format_error` | 格式错误 | P2 |
| `efficiency_issue` | 效率问题 | P2 |

---

## 九、快速对比表：RAG vs Agent 评估

| 维度 | RAG 评估 | Agent 评估 |
|-----|---------|-----------|
| **核心关注** | 检索质量 + 生成忠实度 | 任务完成 + 推理过程 |
| **主要指标** | Faithfulness, Relevance | Task Completion, Reasoning |
| **硬规则** | 引用格式、未找到声明 | 危险操作、安全边界 |
| **过程审计** | 较少关注 | L4 核心关注 |
| **工具评估** | 不涉及 | 核心维度 |
| **协作评估** | 不涉及 | L2 层级 |

---

_快速参考 v1.0 | 2026-04-13_
