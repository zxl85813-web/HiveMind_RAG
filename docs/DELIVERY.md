# HiveMind RAG — 交付文档

> **版本**: v1.0.0-develop
> **日期**: 2026-04-30
> **分支**: `develop` → 已推送至 `origin/develop`
> **最新提交**: `b95d233` feat(quote-intel)

---

## 目录

1. [项目概述](#1-项目概述)
2. [系统架构](#2-系统架构)
3. [本次交付范围](#3-本次交付范围)
4. [各模块详细说明](#4-各模块详细说明)
   - 4.1 多租户治理
   - 4.2 Secrets 管理
   - 4.3 预算与限流
   - 4.4 用量仪表盘
   - 4.5 报价智能 Agent（示例）
5. [Quote Intelligence Agent — 完整流程](#5-quote-intelligence-agent--完整流程)
6. [API 端点清单](#6-api-端点清单)
7. [数据库变更](#7-数据库变更)
8. [文件清单](#8-文件清单)
9. [部署与运行](#9-部署与运行)
10. [安全设计说明](#10-安全设计说明)

---

## 1. 项目概述

HiveMind RAG 是一个企业级多租户 AI 平台，采用 **LangGraph Agent Swarm** 架构，
支持 RAG 知识检索、多模型路由、Skill 插件体系与 MCP 工具集成。

本次交付完成了 **P0 治理能力** 与 **示例 Agent** 两大模块：

| 模块 | 状态 |
|------|------|
| 多租户隔离（ContextVar + 数据库 ACL） | ✅ 已交付 |
| Per-tenant 密钥管理（Fernet 加密） | ✅ 已交付 |
| 预算门禁（6层限速 + 每日费用上限） | ✅ 已交付 |
| 用量仪表盘（前端 30 天趋势图） | ✅ 已交付 |
| 报价智能 Agent（Skill + MCP + 可逆脱敏） | ✅ 已交付 |

---

## 2. 系统架构

```
┌────────────────────────────────────────────────────────────────────┐
│                       前端 React (Vite + Ant Design)                │
│                                                                      │
│  [对话界面]  [知识库管理]  [Agent 可视化]  [用量仪表盘]  [评估面板]   │
└──────────────────────────┬─────────────────────────────────────────┘
                           │ HTTP / SSE / WebSocket
┌──────────────────────────▼─────────────────────────────────────────┐
│                    FastAPI Gateway  /api/v1/                         │
│                                                                      │
│  middleware: TenantContextMiddleware → RateLimiter → BudgetGate     │
│  deps:       JWT → get_current_user → set_current_tenant            │
│              → ensure_loaded(secret_cache)                           │
└──────┬───────────────────┬──────────────────┬───────────────────────┘
       │                   │                  │
┌──────▼──────┐   ┌────────▼────────┐  ┌─────▼──────────────────────┐
│  RAG 模块   │   │  Governance 模块 │  │   Agent Swarm 模块          │
│             │   │                 │  │                              │
│ Knowledge   │   │ SecretManager   │  │ SwarmOrchestrator            │
│ Ingestion   │   │ TokenAccountant │  │   ├── LLMRouter (per-tenant) │
│ Evaluation  │   │ BudgetGate      │  │   ├── SkillRegistry          │
│ Pipelines   │   │ RateLimiter     │  │   │     └── quote-intelligence│
│             │   │ LLMRouter       │  │   └── MCPManager             │
└──────┬──────┘   └────────┬────────┘  │         └── quote-intel-srv  │
       │                   │           └─────────────────┬────────────┘
┌──────▼───────────────────▼───────────────────────────▼────────────┐
│                    数据持久层                                         │
│                                                                      │
│  PostgreSQL (SQLModel + asyncpg + Alembic)                           │
│    tenants / tenant_quotas / tenant_secrets / tenant_usage_daily    │
│    users / conversations / messages / knowledge_bases / documents   │
│    quotes  ← 本次新增                                                │
│                                                                      │
│  Vector DB (Chroma)        Redis (缓存/会话)                         │
│  MinIO (对象存储)           LangFuse (可观测)                        │
└────────────────────────────────────────────────────────────────────┘
```

### 2.1 多租户隔离模型

```
请求进入
  │
  ▼
JWT 解码 → user_id → tenant_id
  │
  ├── ContextVar: tenant_id / user_id / conversation_id
  │    （asyncio.create_task 自动继承）
  │
  ├── RateLimiter.check(tenant_id)       ← 滑动窗口 RPS/RPM
  │
  ├── BudgetGate.check(tenant_id,        ← 6层预算门禁
  │                    user_id,
  │                    conversation_id)
  │
  └── LLMRouter.get_model()              ← 按 tenant 选 API key
```

### 2.2 Agent 流水线

```
用户请求
  │
  ▼
SwarmOrchestrator.invoke_stream()
  │
  ├── pre_processor  → 意图分类 / 知识库路由
  ├── supervisor     → 分配子 Agent
  ├── agent nodes    → 执行 Tools / Skills / MCP
  │     ├── RAG Agent       → 向量检索 + 生成
  │     ├── SQL Agent       → 结构化数据查询
  │     ├── QuoteIntel      → 报价分析（本次示例）
  │     └── ...
  ├── reflection     → 置信度评估 / 自我纠错
  └── END → SSE 流式输出
```

---

## 3. 本次交付范围

### 提交记录

| 提交 | 内容 | 文件数 | 增删 |
|------|------|--------|------|
| `8f053e3` | P0 治理：多租户 + Secrets + 预算门禁 + 限流 + 仪表盘 | 55 | +6733/-336 |
| `b95d233` | 示例 Agent：报价智能（Skill + MCP + 可逆脱敏） | 14 | +550/-2 |

---

## 4. 各模块详细说明

### 4.1 多租户治理

**目标**：每个租户的数据、配额、API Key 完全隔离，互不可见。

**实现**：

```python
# backend/app/core/tenant_context.py
_tenant_ctx: ContextVar[str] = ContextVar("tenant_id")

def tenant_scope(tenant_id, *, user_id=None, conversation_id=None):
    """在 asyncio.create_task 中安全传播 tenant 上下文"""
    ctx = copy_context()
    ctx.run(set_current_tenant, tenant_id)
    ...
```

**数据模型**：

```
tenants            — 租户主表（id, slug, name, plan, is_active）
tenant_quotas      — 配额（max_tokens/day, max_cost/day, max_rpm, max_rps, ...）
tenant_secrets     — 加密密钥（key_name, encrypted_value）
tenant_usage_daily — 每日用量（tokens, requests, cost_usd_micro）
```

**ACL 规则**：所有资源查询均附加 `WHERE tenant_id = $current_tenant`，
返回 404（非 403）以防止跨租户 ID 探测。

---

### 4.2 Secrets 管理

**目标**：租户可自带 LLM API Key，平台不以明文存储任何密钥。

**加密方案**：

```
Master Key (env: SECRET_KEY or SECRETS_MASTER_KEY)
    │
    ▼ HKDF-SHA256 (salt=key_name)
Fernet 派生密钥
    │
    ▼ Fernet.encrypt()
密文存入 tenant_secrets 表
```

**API**（只写，不可读回）：

```
PUT    /api/v1/tenants/{id}/secrets/{key_name}   写入/更新
DELETE /api/v1/tenants/{id}/secrets/{key_name}   撤销
```

**LLM 注入**：`LLMRouter.get_model()` 在 sync 热路径中从内存缓存读取
per-tenant API Key，无数据库 I/O；密钥轮换后调用 `invalidate_tenant()`
清除缓存。

---

### 4.3 预算门禁（6 层）

```
请求到达
  │
  ├── Layer 1: RPS 检查（滑动窗口 1s）     → 429 Retry-After
  ├── Layer 2: RPM 检查（滑动窗口 60s）    → 429 Retry-After
  ├── Layer 3: 租户每日 Token 上限         → 429
  ├── Layer 4: 租户每日费用上限 ($)        → 429
  ├── Layer 5: 单用户每日 Token 上限       → 429
  └── Layer 6: 单会话 Token 上限           → 429

80% 阈值：warn-once-per-day（写入 audit log，不拦截）
```

**成本核算**：

```python
# backend/app/services/governance/token_accountant.py
class BudgetCallbackHandler(BaseCallbackHandler):
    def on_llm_start(self, ..., run_id):
        self._model_by_run[run_id] = model_name   # 捕获模型名
    def on_llm_end(self, response, run_id):
        model = self._model_by_run.pop(run_id)
        prompt_cost, completion_cost = model_cost_table.compute(model, tokens)
        accountant.record(tenant_id, user_id, conversation_id, ...)
```

模型定价表覆盖 30+ 模型（GPT-4o, Claude 3.5, Gemini 2.0, DeepSeek...）。

---

### 4.4 用量仪表盘

**前端页面**：`/usage`（需登录）

功能：
- 今日 Token 用量：进度条（绿/橙/红，阈值 80%/100%）
- 今日费用（USD）：同上
- 30 天趋势 SVG 折线图（Token 数 / 请求数 / 费用）
- 30 秒自动刷新

**API**：
```
GET /api/v1/tenants/{id}/usage           当日快照
GET /api/v1/tenants/{id}/usage/history   30 天历史（零填充缺失天）
```

---

### 4.5 报价智能 Agent（示例）

详见第 5 节。

---

## 5. Quote Intelligence Agent — 完整流程

### 5.1 设计目标

展示 HiveMind RAG 平台如何让 Agent 安全地将 **含 PII 的结构化数据** 交给第三方 LLM 分析：
- **PII 永不离境**：LLM 只看到不透明 token
- **报告可读**：最终回填真实姓名/电话/邮件后交给人类
- **Skill + MCP 双入口**：同一服务代码同时暴露为 Skill 工具和 MCP stdio 工具

### 5.2 Pipeline 图

```
┌──────────────────────────────────────────────────────────────┐
│                  QuoteIntelligenceService                      │
│                                                                │
│  ┌─────────┐   ┌──────────────┐   ┌─────────┐               │
│  │  FETCH  │──▶│     MASK     │──▶│  TOP-N  │               │
│  │         │   │              │   │         │               │
│  │ SELECT  │   │ TokenVault   │   │ score = │               │
│  │ FROM    │   │              │   │ amount  │               │
│  │ quotes  │   │ Alice Chen   │   │ × e^    │               │
│  │ WHERE   │   │ → [CUST_001] │   │ (-age/  │               │
│  │ tenant  │   │ +1-555-1234  │   │  30d)   │               │
│  │ ORDER   │   │ → [PHONE_001]│   │         │               │
│  │ BY date │   │ a@b.com      │   │         │               │
│  │ DESC    │   │ → [EMAIL_001]│   │         │               │
│  └─────────┘   └──────────────┘   └────┬────┘               │
│                                         │                     │
│                    ┌────────────────────▼──────────────────┐ │
│                    │           ANALYZE (LLM)                │ │
│                    │                                        │ │
│                    │  System: "tokens are opaque IDs,       │ │
│                    │           do NOT de-anonymise"         │ │
│                    │                                        │ │
│                    │  Input:  masked JSON (无 PII)          │ │
│                    │  Output: Markdown 报告 (含 token)      │ │
│                    └────────────────────┬──────────────────┘ │
│                                         │                     │
│                    ┌────────────────────▼──────────────────┐ │
│                    │             UNMASK                      │ │
│                    │                                        │ │
│                    │  vault.unmask(report)                  │ │
│                    │  [CUST_001] → Alice Chen               │ │
│                    │  [PHONE_001] → +1-555-1234             │ │
│                    │  [EMAIL_001] → a@b.com                 │ │
│                    │  → 最终报告（PII 回填，供人阅读）       │ │
│                    └───────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### 5.3 阶段详解

#### Stage 0 — 原始数据（DB）

```
quotes 表记录（含 PII）：
  customer_name    = Jack Brown
  customer_phone   = +1-212-555-7788
  customer_email   = jack@lexcorp.us
  customer_company = LexCorp
  product_name     = HiveMind RAG Enterprise
  amount_cents     = 4,990,000   ($49,900 USD)
  region           = AMER
  status           = draft
  created_at       = 2026-04-26
```

#### Stage 1 — Mask（TokenVault）

每个**唯一** PII 值映射到一个稳定 token，同值多次出现 → 同一 token：

```
原始值                          Token
─────────────────────────────   ─────────────
Jack Brown               →      [CUST_001]
+1-212-555-7788          →      [PHONE_001]
jack@lexcorp.us          →      [EMAIL_001]
LexCorp                  →      [COMPANY_001]
Ivy Tanaka               →      [CUST_002]
+81-3-9988-7766          →      [PHONE_002]
ivy@wayne.jp             →      [EMAIL_002]
...（10 客户共 36 个唯一 token）
```

Masked 后记录（送入后续阶段）：
```json
{
  "customer_name":    "[CUST_001]",
  "customer_phone":   "[PHONE_001]",
  "customer_email":   "[EMAIL_001]",
  "customer_company": "[COMPANY_001]",
  "product_name":     "HiveMind RAG Enterprise",
  "amount_cents":     4990000,
  "region":           "AMER",
  "status":           "draft"
}
```

#### Stage 2 — Top-N 排序

```
公式：score = amount_cents × e^(−age_days / 30)

策略可选：
  amount_weighted_recency  ← 默认（金额 × 时间衰减）
  amount_desc              ← 纯金额降序
  recency                  ← 最新优先

实际 TOP-5（masked）：
  #1  [CUST_001]  HiveMind RAG Enterprise  $49,900  draft  2026-04-26
  #2  [CUST_002]  HiveMind RAG Enterprise  $49,900  won    2026-04-20
  #3  [CUST_003]  HiveMind RAG Enterprise  $49,900  draft  2026-04-14
  #4  [CUST_004]  HiveMind RAG Enterprise  $49,900  won    2026-04-08
  #5  [CUST_005]  HiveMind RAG Enterprise  $49,900  draft  2026-04-02
```

#### Stage 3 — LLM 输入（Prompt）

```
System:
  "You are a senior sales-intelligence analyst.
   Customer fields replaced with opaque tokens like [CUST_001].
   Treat tokens as opaque IDs — do NOT invent names, do NOT de-anonymise.
   Produce: ## Executive Summary / ## Top Opportunities / ## Risk & Recommendations"

User:
  "Here are the top 5 masked sales quotes:
   ```json
   [ { "customer_name": "[CUST_001]", "product_name": "HiveMind RAG Enterprise",
       "amount_cents": 4990000, "region": "AMER", "status": "draft", ... },
     ... ]
   ```
   Produce the report now."
```

#### Stage 4 — LLM 输出（含 token，未回填）

```markdown
## Executive Summary
- [CUST_001] 和 [CUST_002] 均持有 Enterprise 报价，合计 $99,800，建议优先跟进。
- 区域 AMER 在 TOP-5 中占比最高，Enterprise 需求旺盛。
- [CUST_003] 状态为 "draft"，可作为本区域拓展标杆案例。

## Top Opportunities

| # | 客户         | 产品                    | 金额    | 状态  |
|---|-------------|-------------------------|---------|-------|
| 1 | [CUST_001]  | HiveMind RAG Enterprise | $49,900 | draft |
| 2 | [CUST_002]  | HiveMind RAG Enterprise | $49,900 | won   |
| 3 | [CUST_003]  | HiveMind RAG Enterprise | $49,900 | draft |
| 4 | [CUST_004]  | HiveMind RAG Enterprise | $49,900 | won   |
| 5 | [CUST_005]  | HiveMind RAG Enterprise | $49,900 | draft |

## Risk & Recommendations
- 联系 [PHONE_001] 时请确认仍为有效号码，该客户最近无互动记录。
- [EMAIL_002] 邮件域名需注意竞争对手背景，沟通时保持信息保密。
- 建议本周对所有 draft 报价发起跟进邮件。
```

#### Stage 5 — Unmask（PII 回填）

```
操作：vault.unmask(report)
  → 单遍正则 re.sub(\[(?:CUST|PHONE|EMAIL|COMPANY)_\d{3,}\])
  → O(文本长度)，不做多轮替换

回填映射（本次报告用到）：
  [CUST_001]   → Jack Brown
  [CUST_002]   → Ivy Tanaka
  [CUST_003]   → Henry Sun
  [CUST_004]   → Grace Park
  [CUST_005]   → Frank Müller
  [PHONE_001]  → +1-212-555-7788
  [EMAIL_002]  → ivy@wayne.jp
```

**最终报告（交给人类读者）**：

```markdown
## Executive Summary
- Jack Brown 和 Ivy Tanaka 均持有 Enterprise 报价，合计 $99,800，建议优先跟进。
- 区域 AMER 在 TOP-5 中占比最高，Enterprise 需求旺盛。
- Henry Sun 状态为 "draft"，可作为本区域拓展标杆案例。

## Top Opportunities

| # | 客户          | 产品                    | 金额    | 状态  |
|---|--------------|-------------------------|---------|-------|
| 1 | Jack Brown   | HiveMind RAG Enterprise | $49,900 | draft |
| 2 | Ivy Tanaka   | HiveMind RAG Enterprise | $49,900 | won   |
| 3 | Henry Sun    | HiveMind RAG Enterprise | $49,900 | draft |
| 4 | Grace Park   | HiveMind RAG Enterprise | $49,900 | won   |
| 5 | Frank Müller | HiveMind RAG Enterprise | $49,900 | draft |

## Risk & Recommendations
- 联系 +1-212-555-7788 时请确认仍为有效号码，该客户最近无互动记录。
- ivy@wayne.jp 邮件域名需注意竞争对手背景，沟通时保持信息保密。
- 建议本周对所有 draft 报价发起跟进邮件。
```

### 5.4 三种调用方式

```
┌────────────────────────────────────────────────────────────────┐
│              QuoteIntelligenceService（核心逻辑）               │
│   app/services/quote/service.py + vault.py                     │
└──────────────────┬──────────────────┬─────────────────────────┘
                   │                  │                  │
         ┌─────────▼──────┐  ┌────────▼──────┐  ┌──────▼────────┐
         │   REST API      │  │  Skill 工具    │  │  MCP 工具     │
         │                 │  │               │  │               │
         │ POST            │  │ quote_intel_  │  │ stdio server  │
         │ /api/v1/quotes/ │  │ run()         │  │ mcp-servers/  │
         │ intelligence/   │  │               │  │ quote-intel-  │
         │ run             │  │ quote_intel_  │  │ server/       │
         │                 │  │ fetch_masked()│  │ server.py     │
         │ JWT 认证        │  │               │  │               │
         │ 租户隔离        │  │ SkillRegistry │  │ mcp_servers.  │
         │                 │  │ 自动发现      │  │ json 配置接入  │
         └─────────────────┘  └───────────────┘  └───────────────┘
```

---

## 6. API 端点清单

### 租户管理

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/tenants` | 列出所有租户（admin） |
| POST | `/api/v1/tenants` | 创建租户 |
| GET | `/api/v1/tenants/{id}` | 获取租户详情 |
| PUT | `/api/v1/tenants/{id}` | 更新租户 |
| DELETE | `/api/v1/tenants/{id}` | 停用租户 |
| PUT | `/api/v1/tenants/{id}/secrets/{key}` | 写入加密密钥（只写） |
| DELETE | `/api/v1/tenants/{id}/secrets/{key}` | 撤销密钥 |
| GET | `/api/v1/tenants/{id}/usage` | 今日用量快照 |
| GET | `/api/v1/tenants/{id}/usage/history` | 30 天历史（零填充） |

### 报价智能

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/quotes/intelligence/run` | 全流程：fetch→mask→top-N→LLM→unmask |

**请求体**：
```json
{
  "top_n": 5,
  "ranking": "amount_weighted_recency",
  "skip_llm": false
}
```

**响应体**：
```json
{
  "fetched_count": 50,
  "selected_count": 5,
  "ranking": "amount_weighted_recency",
  "masked_token_count": 36,
  "masked_records": [...],
  "masked_report": "## Executive Summary\n- [CUST_001] ...",
  "final_report": "## Executive Summary\n- Jack Brown ..."
}
```

---

## 7. 数据库变更

### 迁移历史（全部已应用）

| Revision | 内容 |
|----------|------|
| `a1b2c3d4e5f6` | 多租户：tenants + tenant_quotas + users.tenant_id |
| `b2c3d4e5f6a7` | 多租户 Phase 2：知识库 / 会话 / 文档 tenant 隔离 |
| `c3d4e5f6a7b8` | tenant_usage_daily 每日用量表 |
| `d4e5f6a7b8c9` | 配额扩展：max_cost_usd_micro_per_day, warn_threshold_pct |
| `e5f6a7b8c9d0` | tenant_secrets 加密密钥表 |
| `f6a7b8c9d0e1` | 配额扩展：max_rpm, max_rps, per-user/per-conv Token 上限 |
| `g7c8d9e0f1a2` | **新增**：quotes 表 + 60 行种子数据（10 客户 × 6 产品） |

### quotes 表结构

```sql
CREATE TABLE quotes (
  id                VARCHAR(64)  PRIMARY KEY,
  tenant_id         VARCHAR(64)  NOT NULL DEFAULT 'default',
  customer_name     VARCHAR(128) NOT NULL,   -- PII
  customer_phone    VARCHAR(32)  NOT NULL,   -- PII
  customer_email    VARCHAR(128) NOT NULL,   -- PII
  customer_company  VARCHAR(128),            -- PII
  product_name      VARCHAR(128) NOT NULL,
  quantity          INTEGER      NOT NULL DEFAULT 1,
  unit_price_cents  INTEGER      NOT NULL DEFAULT 0,
  amount_cents      INTEGER      NOT NULL DEFAULT 0,
  currency          VARCHAR(8)   NOT NULL DEFAULT 'USD',
  region            VARCHAR(64),
  status            VARCHAR(16)  NOT NULL DEFAULT 'draft',
  created_at        TIMESTAMP    NOT NULL DEFAULT now()
);
```

---

## 8. 文件清单

### 本次新增 / 变更文件

```
backend/
  alembic/versions/
    g7c8d9e0f1a2_quotes.py          ← 建表 + 60 行种子

  app/
    models/
      quote.py                      ← Quote SQLModel
      __init__.py                   ← 导出 Quote

    api/
      __init__.py                   ← 注册 quotes router
      routes/
        quotes.py                   ← POST /intelligence/run

    services/
      quote/
        __init__.py                 ← 包导出
        vault.py                    ← TokenVault（可逆脱敏）
        service.py                  ← QuoteIntelligenceService

    skills/
      quote_intelligence/
        __init__.py
        SKILL.md                    ← Skill 说明（触发条件 / 安全设计）
        tools.py                    ← quote_intel_run / quote_intel_fetch_masked

mcp-servers/
  quote-intel-server/
    server.py                       ← stdio MCP 服务器
    README.md                       ← 接入配置说明

  (已有)
  quote-intel-server 接入 mcp_servers.json 后即生效

.gitignore                          ← skills/ → /skills/（修复误忽略）
```

### 治理模块（`8f053e3`）关键文件

```
backend/app/services/governance/
  secret_manager.py                 ← FernetBackend + 内存缓存
  token_accountant.py               ← TokenAccountant + BudgetGate + BudgetCallbackHandler
  rate_limiter.py                   ← SlidingWindowRateLimiter
  model_cost_table.py               ← 30+ 模型定价表

backend/app/models/
  tenant.py                         ← Tenant + TenantQuota + TenantSecret
  usage.py                          ← TenantUsageDaily

backend/app/agents/
  llm_router.py                     ← per-tenant API Key 注入

frontend/src/pages/
  UsagePage.tsx                     ← 30 天趋势仪表盘

frontend/src/services/
  tenantsApi.ts                     ← getMyUsage / getMyUsageHistory
```

---

## 9. 部署与运行

### 环境变量

```bash
# 必须
SECRET_KEY=<32+ 字符随机字符串>       # JWT + Fernet 主密钥

# 可选（覆盖 Fernet 主密钥）
SECRETS_MASTER_KEY=<base64url 32B>

# LLM 配置
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
DEFAULT_REASONING_MODEL=o1-preview

# DB
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/hivemind
```

### 启动

```bash
# 后端
cd backend
alembic upgrade head          # 应用所有迁移（包括 quotes 表 + 种子数据）
uvicorn app.main:app --reload

# MCP 服务器接入（可选）
# 编辑 backend/mcp_servers.json，加入 quote_intel 条目后重启后端

# 前端
cd frontend
npm install && npm run dev
```

### 接入 MCP 服务器

编辑 `backend/mcp_servers.json`：

```json
{
  "mcpServers": {
    "test_server": {
      "command": "python",
      "args": ["dummy_mcp_server.py"],
      "type": "stdio"
    },
    "quote_intel": {
      "command": "python",
      "args": ["../mcp-servers/quote-intel-server/server.py"],
      "type": "stdio"
    }
  }
}
```

重启后端后，`SwarmOrchestrator` 的 `MCPManager.connect_all()` 将自动
spawn 服务器并将 `quote_intel_run` / `quote_intel_fetch_masked` 注入 Agent toolset。

---

## 10. 安全设计说明

### PII 保护（TokenVault）

| 威胁 | 防御措施 |
|------|---------|
| LLM 接触明文 PII | vault.mask() 在 LLM 调用前替换所有 PII |
| LLM 猜测或还原 token | System Prompt 明确禁止；即使 LLM 猜出，其输出中的"真实值"不被 vault 识别，unmask 时保持原样 |
| vault 持久化泄露 | vault 仅存在于请求内存，请求结束即销毁，不落库 |
| 日志中出现 PII | 服务代码仅 log tenant_id / count，不 log 记录内容 |

### Secrets 保护（FernetBackend）

| 威胁 | 防御措施 |
|------|---------|
| 密钥明文存库 | HKDF-SHA256 派生密钥 + Fernet AES-128-CBC 加密 |
| API 读回密钥 | PUT-only API，无 GET 接口；返回 hint（末 4 字符）而非明文 |
| 缓存泄露 | 缓存 key = (tenant_id, key_name)，进程内 dict，不暴露到 HTTP |
| 密钥轮换 | 旧 key PUT 新值后 `invalidate_tenant()` 清除 LLMRouter 缓存 |

### 多租户 ACL

| 威胁 | 防御措施 |
|------|---------|
| 跨租户数据访问 | 所有查询 WHERE tenant_id = $current，返回 404（非 403，防探测） |
| 特权提升 | `require_admin()` 依赖拒绝非 admin；tenant_id 来自 JWT（服务端签发） |
| 预算绕过 | BudgetGate 在 middleware 层执行，Swarm 调用前已校验 |

### OWASP Top 10 检查

| 项目 | 状态 |
|------|------|
| A01 Broken Access Control | ✅ 租户 ACL + JWT + require_admin |
| A02 Cryptographic Failures | ✅ Fernet AES-128 + HKDF 派生密钥 |
| A03 Injection | ✅ SQLModel ORM 参数绑定，无拼接 SQL |
| A05 Security Misconfiguration | ✅ SECRET_KEY 必须环境变量，无默认值 |
| A07 Identification & Auth Failures | ✅ JWT HS256 + is_active 检查 |
| A09 Security Logging | ✅ BudgetGate 写入 audit log，80% 预警 |

---

*文档由 GitHub Copilot 自动生成，基于 develop 分支 `b95d233` 状态。*
