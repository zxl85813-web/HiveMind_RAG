# Quick Export · Blueprint → Delivery Package

把平台里"装配好"的 Agent / Skill / MCP / 配置打包成可独立部署的内网交付包。

## 两种用法

### 1. CLI（脚本化、CI 友好）

```bash
# 列出所有可引用的资产
python scripts/export_blueprint.py --list-assets

# 校验一个 blueprint
python scripts/export_blueprint.py blueprints/quote-bot.example.yaml --dry-run

# 导出
python scripts/export_blueprint.py blueprints/quote-bot.example.yaml \
  --output dist/quote-bot --zip --overwrite
```

产出：

```
dist/quote-bot/
  README_DEPLOY.md
  docker-compose.yml
  .env.example
  blueprint.lock.yaml + .json
  backend/                 ← 已按 platform_mode 裁剪
  frontend_dist/           ← 若 frontend/dist 已 build
  skills/<name>/           ← 仅 blueprint 引用的
  mcp-servers/<name>/
dist/quote-bot-1.0.0.zip   ← --zip 时同时产出
```

### 2. UI 向导（推荐给非工程角色）

启动后端 + 前端，访问侧边栏的 **导出交付包**（路由 `/export`）：

| 步骤 | 内容 |
|---|---|
| 1 · 基础 & LLM | 客户名、版本、platform_mode、ui_mode、LLM provider/model |
| 2 · 资产选择 | 多选 skills / MCP servers / 额外路径 |
| 3 · 预览 & 导出 | YAML 实时预览 → 提交后看进度条 → 下载 ZIP |

## 后端 API

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/v1/export/assets` | 资产清单 |
| POST | `/api/v1/export/blueprints/validate` | 校验 |
| POST | `/api/v1/export/jobs` | 提交导出任务 |
| GET | `/api/v1/export/jobs` | 任务列表 |
| GET | `/api/v1/export/jobs/{id}` | 单个任务状态 |
| GET | `/api/v1/export/jobs/{id}/stream` | SSE 进度流 |
| GET | `/api/v1/export/jobs/{id}/download` | 下载 ZIP |
| DELETE | `/api/v1/export/jobs/{id}` | 清理任务 + 产物 |

## 关键文件

| 路径 | 作用 |
|---|---|
| [scripts/_export/schema.py](../scripts/_export/schema.py) | Blueprint pydantic 模型（**单一事实源**）|
| [scripts/_export/assets.py](../scripts/_export/assets.py) | 扫 `skills/` `mcp-servers/` 生成资产清单 |
| [scripts/_export/packager.py](../scripts/_export/packager.py) | 10 步打包流水线 |
| [scripts/export_blueprint.py](../scripts/export_blueprint.py) | CLI |
| [backend/app/services/export_service.py](../backend/app/services/export_service.py) | API 包装 + 后台任务 |
| [backend/app/api/routes/export.py](../backend/app/api/routes/export.py) | 8 个 REST 端点 |
| [frontend/src/pages/ExportWizardPage.tsx](../frontend/src/pages/ExportWizardPage.tsx) | 3 步向导 |
| [frontend/src/services/exportApi.ts](../frontend/src/services/exportApi.ts) | 前端客户端 |
| [frontend/src/stores/blueprintStore.ts](../frontend/src/stores/blueprintStore.ts) | 草稿持久化 (localStorage) |
| [blueprints/quote-bot.example.yaml](../blueprints/quote-bot.example.yaml) | 报价 Bot 示例 blueprint |

## MVP 已知限制

- **单 Agent**：UI 向导目前只编辑第一个 agent；CLI 已支持多个
- **无 docker 镜像 tar**：`--format docker` 留待下一里程碑
- **任务状态在内存**：单容器够用；多副本需要换 Redis
- **YAML 预览只读**：双向 YAML 编辑（Monaco）留待 M4
- **无鉴权**：内网工具默认不加 auth，生产请加保护
