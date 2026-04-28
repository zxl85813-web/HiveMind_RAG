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

## 下一步（Step 2）

完成本步骤后，下一步是：  
**用 Harness Feature Flags 替换 `SERVICE_GOVERNANCE_GRAY_PERCENT` 环境变量**，  
实现 LLM Provider 切换、推理模式开关等 AI 功能的动态灰度控制。
