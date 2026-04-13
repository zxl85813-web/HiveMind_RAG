# DES-015: L5 智体治理任务提报与图谱融合设计

## 1. 背景与动机
在复杂的 Swarm 协作中，Agent 经常会遇到无法自主决策的边界情况。目前的系统缺乏一个结构化的信道将这些“挂起”的决策点转化为可追踪、可审计的任务。本设计旨在通过知识图谱（Neo4j）将这些任务资产化。

## 2. 核心架构

### 2.1 数据模型 (Schema)
在 Neo4j 中引入以下新实体：

#### 2.1.1 `Task` 节点
- `id`: 唯一标识 (UUID)
- `title`: 简要描述
- `priority`: P0-P2
- `status`: `PENDING` | `IN_PROGRESS` | `RESOLVED` | `WONT_FIX`
- `context_stub`: 导致提报的核心矛盾描述
- `suggested_action`: 智体给出的建议操作
- `trace_id`: 关联的执行链路 ID
- `stack_snapshot_url`: 指向本地 Markdown 快照的路径

### 2.2 关系定义
- `(Agent)-[:ESCALATED]->(Task)`: 标识提报人。
- `(Task)-[:RELTES_TO]->(CodeNode)`: 标识受影响的代码模块。
- `(Task)-[:BLOCKS]->(DecisionPoint)`: 标识该任务阻塞了哪个后续决策。

## 3. 工具链设计

### 3.1 `EscalationManager` (Backend)
提供统一的 Python 接口供 `Supervisor` 或 `Reflection` 节点调用：
```python
async def report_unresolved_task(
    title: str, 
    risk: str, 
    reasoning: str,
    affected_nodes: List[str]
) -> str:
    # 1. 生成 Snapshot 文件
    # 2. 写入 Neo4j
    # 3. 触发 TODO.md 更新
    pass
```

### 3.2 `sync_gov_tasks.py` (Sync Engine)
一个定时运行（或由事件触发）的脚本，负责：
- 扫描 `TODO.md` 的 `## 🤖 智体提报任务` 区域。
- 如果发现标记为 `[x]` 的任务，更新 Neo4j 中对应 `Task` 节点的状态为 `RESOLVED`。
- 如果从图谱中发现状态更新，同步回物理文件。

## 4. 交互流程 (Sequence)
1. **Agent** 在推理中发现逻辑死锁或知识真空。
2. **Agent** 调用 `EscalationManager.report_task()`。
3. **Manager** 自动采集当前的 `SwarmState` 片段。
4. **Manager** 更新图谱并向控制台输出提报成功，同时在 `TODO.md` 中追加条目。
5. **Human** 查看 TODO，处理问题，勾选完成。
6. **Sync Script** 将图谱节点置为完成，智体下次重启时通过图谱感知到阻碍已消除。
