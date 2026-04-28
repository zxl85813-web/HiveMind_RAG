# Harness CD 接入指南 — HiveMind RAG

## 概览

本目录包含 HiveMind RAG 的 Harness CD Pipeline 配置。  
部署策略：**Blue/Green with Auto-Rollback**，替代原来的裸 SSH `docker compose up`。

```
.github/workflows/deploy.yml          ← GitHub Actions 触发入口（已改造）
harness/pipelines/production-deploy.yaml  ← Harness Pipeline 定义
scripts/deploy/
  ├── blue_green_deploy.sh            ← 蓝绿部署核心脚本
  ├── rollback.sh                     ← 手动回滚脚本
  └── health_check.sh                 ← 健康检查套件
```

---

## 第一步：Harness 账号与项目配置

### 1.1 注册 Harness（免费 Community Edition）

访问 https://app.harness.io 注册，或自托管：
```bash
# 自托管（需要 4C8G Linux 机器）
docker run -d harness/harness-oss:latest
```

### 1.2 创建 Project

在 Harness UI：
- Organization: `default`（或新建）
- Project Name: `HiveMind RAG`
- Project Identifier: `hivemind_rag`

---

## 第二步：配置 Secrets

在 Harness UI → Project Settings → Secrets 中创建以下 Secret：

| Secret 名称 | 类型 | 说明 |
|---|---|---|
| `azure_server_host` | Text | Azure VM 公网 IP |
| `azure_ssh_key` | SSH Key | 服务器 SSH 私钥 |
| `sonar_token` | Text | SonarQube Token |
| `sonar_host_url` | Text | SonarQube Host URL |
| `slack_webhook_url` | Text | Slack Webhook（可选） |

---

## 第三步：配置 SSH Connector

在 Harness UI → Project Settings → Connectors → New Connector → SSH:

```
Name:        Azure Production Server
Identifier:  azure_prod_ssh
Host:        <+secrets.getValue("azure_server_host")>
Port:        22
Username:    azureuser
Auth:        SSH Key → 选择 azure_ssh_key
```

测试连接通过后保存。

---

## 第四步：导入 Pipeline

### 方式 A：通过 Harness UI 导入 YAML

1. 进入 Project → Pipelines → Import Pipeline
2. 上传 `harness/pipelines/production-deploy.yaml`
3. 检查 Variables 中的默认值是否正确

### 方式 B：通过 Harness API 创建

```bash
curl -X POST \
  "https://app.harness.io/pipeline/api/pipelines?accountIdentifier=YOUR_ACCOUNT_ID&orgIdentifier=default&projectIdentifier=hivemind_rag" \
  -H "x-api-key: YOUR_HARNESS_API_KEY" \
  -H "Content-Type: application/yaml" \
  --data-binary @harness/pipelines/production-deploy.yaml
```

---

## 第五步：配置 GitHub Secrets

在 GitHub Repository → Settings → Secrets and variables → Actions：

| Secret 名称 | 说明 |
|---|---|
| `HARNESS_API_KEY` | Harness Personal Access Token（在 Harness → My Profile → API Keys 生成） |
| `HARNESS_ACCOUNT_ID` | Harness Account ID（在 Harness → Account Settings 查看） |

在 GitHub Repository → Settings → Variables：

| Variable 名称 | 默认值 | 说明 |
|---|---|---|
| `HARNESS_ORG_ID` | `default` | Harness Org Identifier |
| `HARNESS_PROJECT_ID` | `hivemind_rag` | Harness Project Identifier |
| `HARNESS_PIPELINE_ID` | `hivemind_production_deploy` | Harness Pipeline Identifier |

---

## 部署流程说明

### 正常部署流程

```
push to main
    │
    ▼
GitHub Actions: deploy.yml
    │
    ├─ Job 1: SonarQube Scan
    │
    └─ Job 2a: Trigger Harness Pipeline
           │
           ▼
       Harness CD Pipeline
           │
           ├─ Stage 1: Pre-Deploy Validation
           │     └─ 验证服务器环境
           │
           ├─ Stage 2: Blue/Green Deploy
           │     ├─ 确定 active/standby slot
           │     ├─ 在 standby 上构建新版本
           │     ├─ 健康检查（36次重试，3分钟）
           │     ├─ 数据库迁移
           │     └─ 切换 active slot
           │
           └─ Stage 3: Post-Deploy Verification
                 ├─ 验证容器状态
                 ├─ API 端点检查
                 └─ Slack 通知
```

### 自动回滚触发条件

- 健康检查超时（3分钟内未变为 healthy）
- 容器报告 unhealthy 状态
- 数据库迁移失败
- 冒烟测试 HTTP 非 200

回滚时：
1. 停止失败的 standby slot
2. 确认原 active slot 仍在运行
3. 不修改 state file（active slot 不变）

### 手动回滚

```bash
# SSH 进服务器
ssh azureuser@YOUR_SERVER_IP

# 执行回滚
cd /home/azureuser/HiveMind_RAG
./scripts/deploy/rollback.sh

# 或强制回滚到指定 slot
./scripts/deploy/rollback.sh --slot blue
```

---

## 降级方案（Harness 未配置时）

如果 `HARNESS_API_KEY` 未配置，`deploy.yml` 会自动降级到直接 SSH 模式，  
同样使用 `blue_green_deploy.sh`，只是没有 Harness 的可视化和审计能力。

也可以手动触发直接模式：
- GitHub Actions → deploy.yml → Run workflow → deploy_mode: `direct`

---

## 蓝绿 Slot 状态查看

```bash
# 查看当前活跃 slot
cat /home/azureuser/HiveMind_RAG/.deploy_state

# 查看所有容器状态
docker ps --filter "name=hivemind"

# 查看部署日志
ls -lt /home/azureuser/HiveMind_RAG/logs/deploy/
tail -f /home/azureuser/HiveMind_RAG/logs/deploy/deploy_latest.log
```

---

## 下一步（Step 4）

完成本步骤后，下一步是：  
**RAG 评估门禁接入 Policy as Code 做成本控制**，防止 LLM API 费用失控。

---

## Step 2：Feature Flags 接入指南

### 新增文件

```
backend/app/sdk/feature_flags/
  ├── __init__.py      # 单例入口：from app.sdk.feature_flags import ff
  ├── flags.py         # Flag 注册表（所有 flag 的定义、类型、降级字段）
  └── service.py       # FeatureFlagService（优先级链 + 缓存 + 快照）
```

### 已接入的 Flag

| Flag Key | 类型 | 替换的 settings 字段 | 说明 |
|---|---|---|---|
| `nvidia_thinking_enabled` | bool | `NVIDIA_THINKING_ENABLED` | NVIDIA NIM 推理模式开关 |
| `nvidia_reasoning_effort` | string | `NVIDIA_REASONING_EFFORT` | 推理强度 low/medium/max |
| `reasoning_provider` | string | `REASONING_PROVIDER` | 推理层 Provider 动态切换 |
| `default_reasoning_model` | string | `DEFAULT_REASONING_MODEL` | 推理层模型名称 |
| `default_complex_model` | string | `DEFAULT_COMPLEX_MODEL` | Complex 层模型名称 |
| `service_gray_percent` | int | `SERVICE_GOVERNANCE_GRAY_PERCENT` | 服务治理灰度百分比 |
| `service_topology_mode` | string | `SERVICE_TOPOLOGY_MODE` | 服务拓扑模式 |
| `debate_mode_enabled` | bool | —（新增）| 多模型辩论引擎开关 |
| `swarm_ab_test_enabled` | bool | —（新增）| Swarm A/B 测试开关 |
| `rag_hallucination_breaker` | bool | —（新增）| 幻觉熔断器开关 |
| `llm_cost_daily_limit_usd` | float | `BUDGET_DAILY_LIMIT_USD` | LLM 每日成本上限 |

### 配置 Harness Feature Flags

**1. 安装 SDK**
```bash
pip install harness-featureflags
```

**2. 在 `.env` 中添加 SDK Key**
```bash
HARNESS_FF_SDK_KEY=sdk-your-harness-ff-sdk-key
```

**3. 在 Harness UI 创建 Flag**

进入 Harness → Feature Flags → New Feature Flag：
- Flag Type: `Boolean` 或 `Multivariate`
- Identifier: 与上表 Flag Key 完全一致
- Default Rules: 按需配置

**4. 验证接入**
```bash
# 查看所有 flag 当前值和来源
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/observability/feature-flags

# 修改 Harness 控制台后强制刷新缓存（无需等待 30s TTL）
curl -X POST -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/observability/feature-flags/invalidate"
```

### 降级行为

`HARNESS_FF_SDK_KEY` 未配置时，所有 flag 自动从 `settings` 环境变量读取，  
行为与改造前完全一致，**不影响现有功能**。

### 新增 Flag 的方法

只需在 `backend/app/sdk/feature_flags/flags.py` 的 `REGISTRY` 中添加一条：

```python
"my_new_flag": FlagDefinition(
    key="my_new_flag",
    flag_type=FlagType.BOOL,
    settings_fallback="MY_SETTINGS_FIELD",  # 降级字段，没有则填 ""
    default=False,
    description="说明这个 flag 控制什么",
    tags=["ai-features"],
),
```

无需修改其他任何文件。

---

## Step 4：RAG 评估门禁 Policy as Code

### 新增文件

```
scripts/ci/
  ├── rag_eval_budget_guard.py   # 预算守卫：触发策略 + 预算检查 → 决定 real/mock
  └── rag_eval_mock.py           # Mock 评估：零 LLM 调用，验证流程完整性

harness/policies/
  ├── rag_eval_trigger_policy.rego  # OPA Policy：触发条件规则
  └── rag_eval_budget_policy.rego   # OPA Policy：预算上限规则
```

### 改造文件

- `.github/workflows/rag-eval-gate.yml` — 加入 budget-guard job，分离 real/mock 两条路径
- `.github/workflows/hmer-architecture-eval.yml` — LLM 报告生成步骤加预算保护，后端启动改为健康检查等待

### 触发决策矩阵

| 触发场景 | 评估模式 | 原因 |
|---|---|---|
| `workflow_dispatch` | ✅ Real | 手动触发，始终真实 |
| `push` → `main` | ✅ Real | 生产门禁 |
| `release/*` PR → `main` | ✅ Real | 发布前验证 |
| `push` → `develop` + RAG 核心路径变更 | ✅ Real | 核心逻辑变更 |
| `push` → `develop` + 无 RAG 核心路径变更 | 🎭 Mock | 无关变更，节省成本 |
| feature PR → `develop` | 🎭 Mock | 快速反馈，零成本 |
| 日预算 ≥ 80% | 🎭 Mock（降级） | 预算保护 |
| 月预算 ≥ 90% | 🎭 Mock（降级） | 预算保护 |

### 成本追踪配置

在 GitHub Repository → Settings → Variables 中设置（可选，用于跨 runner 共享成本数据）：

| Variable | 说明 |
|---|---|
| `CI_DAILY_LLM_COST_USD` | 当日已消耗 LLM 成本（USD），由外部系统更新 |
| `CI_MONTHLY_LLM_COST_USD` | 当月已消耗 LLM 成本（USD） |

不设置时，使用本地 `.ci_cost_cache.json` 缓存（通过 `actions/cache` 跨 run 持久化）。

### 接入 Harness OPA

1. 进入 Harness → Project Settings → Policies → New Policy
2. 分别上传 `rag_eval_trigger_policy.rego` 和 `rag_eval_budget_policy.rego`
3. 在 Pipeline 的 RAG 评估 Stage 前添加 Policy Step，绑定上述两个 Policy
4. Harness 会在 Pipeline 执行前自动评估 Policy，不通过时阻断执行

本地测试 OPA Policy（需要安装 [opa CLI](https://www.openpolicyagent.org/docs/latest/#running-opa)）：
```bash
# 测试触发策略
opa eval -d harness/policies/rag_eval_trigger_policy.rego \
  -i '{"event":"push","branch":"develop","source_branch":"","changed_paths":["backend/app/prompts/system.txt"],"force_real":false}' \
  "data.hivemind.rag_eval.trigger"

# 测试预算策略
opa eval -d harness/policies/rag_eval_budget_policy.rego \
  -i '{"requested_mode":"real_eval","daily_cost_usd":8.5,"monthly_cost_usd":45.0,"daily_limit_usd":10.0,"monthly_limit_usd":100.0}' \
  "data.hivemind.rag_eval.budget.allow"
```
