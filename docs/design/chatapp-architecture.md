# 🎭 ChatApp — Flutter + FastAPI 聊天应用架构设计

> **定位**: 以聊天/角色扮演为核心的移动端 App，兼容 SillyTavern 角色卡生态，  
> 后端复用 HiveMind RAG 架构，前端 Flutter 跨平台。

> 📅 创建日期: 2026-02-24

---

## 一、SillyTavern 角色卡格式深度分析

### 1.1 角色卡 JSON 结构（以 `夏瑾 Pro 比邻星 1.90.json` 为例）

酒馆的 "预设" 实际是一个复杂的 **Prompt 编排系统**，不是简单的 system prompt。

```
角色卡 JSON
├── 🔧 模型参数 (Model Settings)
│   ├── temperature: 1.2
│   ├── top_p: 1
│   ├── top_k / top_a / min_p / repetition_penalty
│   ├── openai_max_context: 2000000   ← 最大上下文窗口
│   ├── openai_max_tokens: 8192       ← 最大输出 token
│   └── stream_openai: true           ← 流式输出
│
├── 📋 Prompt 条目列表 (prompts[])
│   │   每个条目 = { identifier, name, role, content, enabled, system_prompt,
│   │               injection_position, injection_depth, forbid_overrides, marker }
│   │
│   ├── 🏷️ Marker 类型 (占位符/锚点)
│   │   ├── charDescription      → 角色描述插入点
│   │   ├── charPersonality      → 角色性格插入点
│   │   ├── scenario             → 场景插入点
│   │   ├── dialogueExamples     → 对话示例插入点
│   │   ├── chatHistory          → 聊天历史插入点
│   │   ├── worldInfoBefore/After → 世界书前/后插入点
│   │   └── personaDescription   → 用户人设插入点
│   │
│   ├── ⚙️ 系统级条目 (system_prompt: true, 核心框架)
│   │   ├── "🛡️系统提示" (enhanceDefinitions) → 基础身份: "你是Haruki..."
│   │   ├── "📘字数设置" → 变量驱动: {{setvar::wordsCloud::大约1500}}
│   │   ├── "🛡️变量" (jailbreak) → 核心变量池: 多个 {{setvar::...}} 宏
│   │   └── "➡️扩写/转述输入" (main) → 主指令
│   │
│   ├── 🎨 可选模组 (enabled: false, 用户按需开启)
│   │   ├── 文风模组: 🖋️默认/心理流/日本纯文学/武侠/轻小说/零度写作/电影式/沉浸式
│   │   ├── NSFW 模组: 🌸色情描写/NSFW基础/NSFW强化/限速器/温柔化
│   │   ├── 控制模组: 🧭慢速推进/中速/快速/爆炸式/剧情推进
│   │   ├── 防护模组: 🧊抗绝望/抗发情/抗霸总/抗机器人/抗八股/反全知
│   │   ├── 角色控制: 防抢话/自由抢话/第二人称/第三人称/集中AI角色
│   │   ├── 格式模组: 思维链/小总结/状态姬/格式姬/填表姬
│   │   └── 预填充/破限: 强破限/预填充模式/原生模式/分析助手模式
│   │
│   └── 📐 SPreset 配置 (嵌入的高级配置)
│       ├── ChatSquash (合并消息配置)
│       └── RegexBinding (正则脚本绑定)
│
├── 📊 Prompt 排序 (prompt_order[])
│   │   决定所有 prompts 的最终**发送顺序**
│   ├── character_id: 100000 → 默认排序
│   └── character_id: 100001 → 自定义排序 (实际使用的)
│
├── 🔗 正则脚本 (extensions.regex_scripts[])
│   ├── 【云瑾】包裹最新指示 → 用户输入套 <最新互动> 标签
│   ├── 【云瑾】移除额外tag → 清理 AI 输出的元标签
│   ├── 【云瑾】八股抹除 → 正则删除滥用词汇
│   ├── 【云瑾】切除小总结 → 管理上下文窗口
│   └── 【夏瑾】底部正则 → 消息包装
│
└── 🧰 其他
    ├── assistant_prefill / assistant_impersonation
    ├── show_thoughts: true (显示思维过程)
    ├── reasoning_effort: "medium"
    └── SPreset (高级预设插件配置)
```

### 1.2 核心机制解析

| 机制 | 说明 | 后端实现策略 |
|:-----|:-----|:------------|
| **宏变量 (Macros)** | `{{setvar::name::value}}` / `{{getvar::name}}` / `{{user}}` / `{{lastusermessage}}` / `{{roll 1d999999}}` / `{{random::a,b,...}}` / `{{trim}}` | 实现 `MacroEngine` 解析器 |
| **注入位置 (Injection)** | `injection_position` + `injection_depth` 控制 prompt 在消息流中的精确位置 | `PromptAssembler` 按深度插入 system 消息 |
| **Prompt 排序 (Order)** | `prompt_order` 定义全局组装顺序 | 后端按 order 数组排序激活条目 |
| **Marker 占位符** | `charDescription` 等 marker 条目不发送内容，仅标记插入位置 | 在组装时替换为角色卡对应字段 |
| **正则脚本 (Regex)** | 对输入/输出做正则替换，分 prompt 侧和 display 侧 | `RegexPipeline` 前后处理器 |
| **模组开关** | 用户可自由启用/禁用 prompt 条目 | 前端 Toggle + 持久化到用户配置 |

---

## 二、项目架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────┐
│                    Flutter App (跨平台)                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │  聊天核心  │  │  角色卡   │  │ Token面板 │  │  设置   │ │
│  │ SSE流式   │  │ 导入/管理 │  │ 用量统计  │  │ 加密/推 │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬────┘ │
│       │             │             │              │       │
│  ┌────┴─────────────┴─────────────┴──────────────┴────┐ │
│  │              Core Layer (Dio/SSE/WebSocket)         │ │
│  └────────────────────────┬───────────────────────────┘ │
└───────────────────────────┼─────────────────────────────┘
                            │ HTTPS/WSS (E2E 加密)
┌───────────────────────────┼─────────────────────────────┐
│                    FastAPI Backend                        │
│  ┌────────────────────────┴───────────────────────────┐ │
│  │                   API Gateway                       │ │
│  ├──────────┬──────────┬──────────┬──────────────────┤ │
│  │  Chat    │  Preset  │  Token   │  User/Auth       │ │
│  │  Routes  │  Routes  │  Routes  │  Routes          │ │
│  ├──────────┴──────────┴──────────┴──────────────────┤ │
│  │              Service Layer                         │ │
│  ├──────────┬──────────┬──────────┬──────────────────┤ │
│  │  Chat    │  Preset  │ Token    │  Notification    │ │
│  │  Service │  Engine  │ Pool     │  Service (FCM)   │ │
│  ├──────────┴──────────┴──────────┴──────────────────┤ │
│  │              Infrastructure                        │ │
│  │  ┌─────────┐ ┌───────────┐ ┌─────────────┐       │ │
│  │  │ Prompt  │ │ LLM Router│ │ Macro Engine│       │ │
│  │  │Assembler│ │ + TokenPool│ │ + Regex Pipe│       │ │
│  │  └─────────┘ └───────────┘ └─────────────┘       │ │
│  ├───────────────────────────────────────────────────┤ │
│  │  Database (PostgreSQL) │ Redis (Cache/Session)     │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 2.2 目录结构

```
chatapp/
├── .agent/                              # 研发治理 (从 HiveMind 迁移)
│   ├── rules/
│   │   ├── coding-standards.md          # ← 迁移
│   │   ├── project-structure.md         # 🆕 适配新项目
│   │   └── flutter-standards.md         # 🆕 Flutter 编码规范
│   ├── workflows/
│   │   ├── develop-feature.md           # ← 迁移
│   │   ├── create-api.md               # ← 迁移
│   │   └── create-screen.md            # 🆕 Flutter 页面创建流程
│   └── checks/
│       └── code_quality.py             # ← 迁移
│
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI 入口
│   │   ├── core/                       # ← 迁移 HiveMind core/
│   │   │   ├── config.py              # 全局配置
│   │   │   ├── database.py            # SQLModel + Alembic
│   │   │   ├── security.py            # JWT 认证 + E2E 加密支持
│   │   │   ├── exceptions.py          # 统一异常
│   │   │   └── logging.py             # Loguru 日志
│   │   │
│   │   ├── api/routes/
│   │   │   ├── chat.py                # 🔑 聊天 SSE 流式
│   │   │   ├── presets.py             # 🆕 角色卡/预设 CRUD + 导入
│   │   │   ├── token_pool.py          # 🆕 API Key 池管理
│   │   │   ├── auth.py                # 认证注册
│   │   │   ├── users.py               # 用户管理
│   │   │   ├── stats.py               # 🆕 Token 用量统计
│   │   │   └── health.py              # 健康检查
│   │   │
│   │   ├── models/
│   │   │   ├── user.py                # 用户表
│   │   │   ├── chat.py                # 会话 + 消息表
│   │   │   ├── preset.py              # 🆕 角色卡/预设表
│   │   │   ├── api_key.py             # 🆕 API Key 池表
│   │   │   └── token_usage.py         # 🆕 Token 用量表
│   │   │
│   │   ├── schemas/
│   │   │   ├── chat.py
│   │   │   ├── preset.py              # 🆕 酒馆卡格式 Schema
│   │   │   ├── token_pool.py          # 🆕
│   │   │   └── stats.py               # 🆕
│   │   │
│   │   ├── services/
│   │   │   ├── chat_service.py        # 🔑 聊天核心 (SSE/消息编排)
│   │   │   ├── preset_engine.py       # 🆕 角色卡解析 + Prompt 组装
│   │   │   ├── macro_engine.py        # 🆕 宏变量解析器
│   │   │   ├── regex_pipeline.py      # 🆕 正则脚本管道
│   │   │   ├── token_pool_service.py  # 🆕 Key 池负载均衡
│   │   │   └── notification_service.py # 🆕 FCM 推送
│   │   │
│   │   ├── llm/                       # ← 迁移 + 完善
│   │   │   ├── router.py              # 多模型路由
│   │   │   ├── token_pool.py          # 🆕 Key 池核心逻辑
│   │   │   └── guardrails.py          # 安全护栏
│   │   │
│   │   └── prompts/                   # ← 迁移 Prompt 体系
│   │       ├── engine.py
│   │       ├── loader.py
│   │       └── templates/
│   │
│   ├── alembic/                       # 数据库迁移
│   ├── tests/
│   └── requirements.txt
│
├── flutter_app/                        # 🆕 Flutter 前端
│   ├── lib/
│   │   ├── main.dart
│   │   ├── app/
│   │   │   ├── app.dart               # MaterialApp 根组件
│   │   │   ├── routes.dart            # GoRouter 路由
│   │   │   └── theme/
│   │   │       ├── app_theme.dart     # 主题定义 (暗色/亮色)
│   │   │       └── colors.dart        # 调色板
│   │   │
│   │   ├── core/
│   │   │   ├── api/
│   │   │   │   ├── api_client.dart    # Dio 封装 (拦截器/认证/重试)
│   │   │   │   └── endpoints.dart     # API 端点常量
│   │   │   ├── sse/
│   │   │   │   └── sse_client.dart    # SSE 流式连接管理
│   │   │   ├── websocket/
│   │   │   │   └── ws_client.dart     # WebSocket 实时推送
│   │   │   ├── encryption/
│   │   │   │   └── e2e_crypto.dart    # 🔐 E2E 加密工具
│   │   │   └── storage/
│   │   │       └── local_db.dart      # Hive / SQLite 本地存储
│   │   │
│   │   ├── features/
│   │   │   ├── chat/                  # 🔑 核心聊天模块
│   │   │   │   ├── models/
│   │   │   │   │   ├── message.dart
│   │   │   │   │   └── conversation.dart
│   │   │   │   ├── providers/         # Riverpod 状态管理
│   │   │   │   │   ├── chat_provider.dart
│   │   │   │   │   └── sse_provider.dart
│   │   │   │   ├── screens/
│   │   │   │   │   ├── chat_list_screen.dart    # 会话列表
│   │   │   │   │   └── chat_detail_screen.dart  # 聊天详情
│   │   │   │   └── widgets/
│   │   │   │       ├── message_bubble.dart       # 消息气泡
│   │   │   │       ├── typing_indicator.dart     # ⭐ 流式打字效果
│   │   │   │       ├── markdown_renderer.dart    # Markdown 渲染
│   │   │   │       └── chat_input_bar.dart       # 输入栏
│   │   │   │
│   │   │   ├── presets/               # 🆕 角色卡模块
│   │   │   │   ├── models/
│   │   │   │   │   └── preset.dart    # 酒馆卡 Dart 模型
│   │   │   │   ├── providers/
│   │   │   │   │   └── preset_provider.dart
│   │   │   │   ├── screens/
│   │   │   │   │   ├── preset_gallery_screen.dart  # 角色卡画廊
│   │   │   │   │   └── preset_detail_screen.dart   # 预设详情/开关
│   │   │   │   └── widgets/
│   │   │   │       ├── preset_card.dart        # 角色卡卡片
│   │   │   │       └── module_toggle.dart      # 模组开关列表
│   │   │   │
│   │   │   ├── token_stats/           # 🆕 Token 用量面板
│   │   │   │   ├── providers/
│   │   │   │   ├── screens/
│   │   │   │   │   └── token_dashboard_screen.dart
│   │   │   │   └── widgets/
│   │   │   │       ├── usage_chart.dart        # 用量图表
│   │   │   │       ├── cost_summary.dart       # 费用摘要
│   │   │   │       └── key_status_card.dart    # Key 状态卡片
│   │   │   │
│   │   │   ├── settings/              # 设置模块
│   │   │   │   └── screens/
│   │   │   │       ├── settings_screen.dart
│   │   │   │       ├── api_keys_screen.dart    # Key 池管理
│   │   │   │       └── security_screen.dart    # 🔐 E2E 加密设置
│   │   │   │
│   │   │   └── auth/                  # 认证模块
│   │   │       ├── screens/
│   │   │       └── providers/
│   │   │
│   │   └── shared/
│   │       ├── widgets/               # 共享组件
│   │       ├── utils/                 # 工具函数
│   │       └── constants/             # 常量
│   │
│   ├── pubspec.yaml
│   └── test/
│
├── docs/
│   └── design/
│       └── chatapp-architecture.md    # 本文件
│
├── REGISTRY.md
├── TODO.md
└── README.md
```

---

## 三、核心模块设计

### 3.1 角色卡/预设引擎 (Preset Engine)

这是整个 App 最关键的差异化组件，需要完全兼容 SillyTavern 角色卡格式。

#### 3.1.1 数据模型

```python
# backend/app/models/preset.py

class Preset(SQLModel, table=True):
    """角色卡/预设主表"""
    id: UUID
    name: str                          # 预设名称, e.g. "夏瑾 Pro 比邻星 1.90"
    description: str | None
    avatar_url: str | None
    
    # === 模型参数 ===
    temperature: float = 1.0
    top_p: float = 1.0
    top_k: int = 0
    min_p: float = 0.0
    repetition_penalty: float = 1.0
    max_context: int = 128000
    max_tokens: int = 4096
    stream: bool = True
    
    # === Prompt 条目 (JSON 存储) ===
    prompts: dict                      # 完整 prompts[] 数组
    prompt_order: dict                 # 排序配置
    
    # === 正则脚本 (JSON) ===
    regex_scripts: dict | None         # extensions.regex_scripts
    
    # === 扩展配置 (JSON) ===
    extensions: dict | None            # SPreset 等高级配置
    
    # === 元信息 ===
    source: str = "import"             # import | custom | shared
    original_filename: str | None
    is_active: bool = True
    usage_count: int = 0
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


class PresetModuleOverride(SQLModel, table=True):
    """用户对预设模组的个性化开关状态"""
    id: UUID
    user_id: UUID
    preset_id: UUID
    module_identifier: str             # prompt 条目的 identifier
    enabled: bool                      # 用户是否启用
    custom_content: str | None         # 用户自定义覆写内容 (可选)
```

#### 3.1.2 Prompt 组装流水线

```
用户发送消息
    │
    ▼
┌───────────────────────┐
│  1. 加载当前预设配置     │
│     (Preset + Overrides)│
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│  2. 过滤活跃条目         │
│     prompt_order 排序   │
│     + enabled 过滤      │
│     + user overrides    │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│  3. 宏变量解析           │
│     MacroEngine.resolve │
│     {{setvar}} {{getvar}}│
│     {{user}} {{trim}}   │
│     {{lastusermessage}} │
│     {{random}} {{roll}} │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│  4. Marker 替换          │
│     charDescription →   │
│       角色卡 description │
│     chatHistory →       │
│       历史消息           │
│     personaDescription →│
│       用户人设           │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│  5. 注入深度处理          │
│     injection_depth     │
│     控制 system prompt  │
│     在消息流中的位置      │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│  6. 正则输入处理          │
│     RegexPipeline       │
│     placement: [1]      │
│     (prompt侧)          │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│  7. 组装最终 messages[]  │
│     → 发给 LLM API      │
└───────────┬───────────┘
            │
    LLM 返回流式响应
            │
            ▼
┌───────────────────────┐
│  8. 正则输出处理          │
│     placement: [2]      │
│     (display侧)         │
│     八股抹除/标签清理     │
└───────────┘
```

#### 3.1.3 宏引擎 (MacroEngine)

```python
# backend/app/services/macro_engine.py

class MacroEngine:
    """解析酒馆宏变量语法"""
    
    def __init__(self, context: dict):
        self._vars: dict[str, str] = {}
        self._context = context  # user, char, lastusermessage 等
    
    def resolve(self, text: str) -> str:
        """解析所有宏"""
        text = self._resolve_setvar(text)    # {{setvar::key::value}}
        text = self._resolve_getvar(text)    # {{getvar::key}}
        text = self._resolve_builtins(text)  # {{user}}, {{char}}, {{lastusermessage}}
        text = self._resolve_random(text)    # {{random::a,b,c}}
        text = self._resolve_roll(text)      # {{roll 1d999999}}
        text = self._resolve_trim(text)      # {{trim}}
        text = self._resolve_comments(text)  # {{//注释内容}}
        return text
```

---

### 3.2 API Token 池 — 负载均衡引擎

#### 3.2.1 数据模型

```python
# backend/app/models/api_key.py

class ApiKeyPool(SQLModel, table=True):
    """API Key 池"""
    id: UUID
    provider: str                    # openai / deepseek / gemini / claude / siliconflow
    alias: str                       # 显示名 (不暴露真实 key)
    encrypted_key: str               # AES-256 加密存储
    base_url: str                    # API 端点
    supported_models: list[str]      # 可用模型列表
    
    # === 限速配置 ===
    rpm_limit: int = 60              # 每分钟请求上限
    tpm_limit: int = 100000          # 每分钟 Token 上限
    daily_quota_usd: float = 10.0    # 日预算 ($)
    
    # === 路由权重 ===
    priority: int = 0                # 权重 (越高越优先)
    is_active: bool = True
    
    # === 运行时状态 (Redis 缓存) ===
    # current_rpm, current_tpm → Redis 滑动窗口
    # cooldown_until → Redis TTL key
    
    # === 统计 ===
    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    last_error: str | None = None
    last_used_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class TokenUsageLog(SQLModel, table=True):
    """Token 使用明细日志"""
    id: UUID
    user_id: UUID
    conversation_id: UUID
    message_id: UUID
    api_key_id: UUID                 # 使用了哪个 Key
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float                  # 计算费用
    latency_ms: int                  # 响应延迟
    is_success: bool
    error_message: str | None
    created_at: datetime
```

#### 3.2.2 负载均衡策略

```python
# backend/app/llm/token_pool.py

class LoadBalanceStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"          # 轮询
    WEIGHTED = "weighted"                 # 按 priority 权重
    LEAST_USED = "least_used"            # 最少使用
    LOWEST_LATENCY = "lowest_latency"    # 最低延迟

class TokenPoolManager:
    """
    API Key 池管理器
    
    核心流程:
    1. acquire_key(model, strategy) → 获取可用 Key
    2. 检查 RPM/TPM 限速 (Redis 滑动窗口)
    3. 检查冷却期 (429 后自动冷却)
    4. 检查日预算
    5. 按策略选择 Key
    6. release_key(key_id, usage) → 归还并更新统计
    """
    
    async def acquire_key(self, model: str, strategy: LoadBalanceStrategy) -> ApiKeyEntry:
        # 1. 查询所有支持该 model 的活跃 Key
        candidates = await self._get_candidates(model)
        
        # 2. 过滤: 冷却中 / 超限 / 超预算的 Key
        available = [k for k in candidates if await self._is_available(k)]
        
        if not available:
            raise NoAvailableKeyError(f"No available API key for model: {model}")
        
        # 3. 按策略选择
        match strategy:
            case LoadBalanceStrategy.ROUND_ROBIN:
                return self._round_robin(available)
            case LoadBalanceStrategy.WEIGHTED:
                return self._weighted_random(available)
            case LoadBalanceStrategy.LEAST_USED:
                return self._least_used(available)
            case LoadBalanceStrategy.LOWEST_LATENCY:
                return self._lowest_latency(available)
    
    async def report_error(self, key_id: UUID, error: Exception):
        """报告错误，触发冷却"""
        if is_rate_limit_error(error):  # 429
            await self._cooldown(key_id, cooldown_seconds=60)
        elif is_auth_error(error):       # 401/403
            await self._deactivate(key_id)
    
    async def get_usage_stats(self, time_range: str) -> TokenUsageStats:
        """获取用量统计 (用于 Token 面板)"""
        ...
```

---

### 3.3 E2E 端到端加密

```
┌─────────────┐                    ┌─────────────┐
│  Flutter App │                    │   Backend   │
│              │                    │             │
│  1. 生成密钥对 │                   │  仅存储密文  │
│  (X25519)    │                    │  无法解密    │
│              │                    │             │
│  2. 加密消息  │──── 密文 ────────▶│  3. 存储密文 │
│  (AES-256-GCM)                    │             │
│              │                    │  4. 转发密文 │
│  5. 解密消息  │◀─── 密文 ────────│             │
│              │                    │             │
└─────────────┘                    └─────────────┘

加密范围: 用户消息内容 + AI 回复内容
不加密: 消息元数据 (时间戳、会话ID、token统计)
```

**实现方案**:
- 客户端: `pointycastle` (Dart 加密库) 或 `libsodium` (通过 FFI)
- 密钥存储: Flutter Secure Storage (Keychain/Keystore)
- 加密算法: X25519 密钥交换 + AES-256-GCM 对称加密
- 场景: 用户可选择对特定会话开启 E2E 加密

---

### 3.4 流式打字效果 (Flutter)

```dart
// flutter_app/lib/features/chat/widgets/typing_indicator.dart

class StreamingMessageWidget extends StatefulWidget {
  final Stream<String> tokenStream;  // SSE Token 流
  
  @override
  State<StreamingMessageWidget> createState() => _StreamingMessageState();
}

class _StreamingMessageState extends State<StreamingMessageWidget> {
  final StringBuffer _buffer = StringBuffer();
  
  // 逐字追加，带光标闪烁动画
  // 支持 Markdown 实时渲染 (flutter_markdown)
  // 代码块高亮 (flutter_highlight)
  // LaTeX 公式 (flutter_math_fork)
}
```

**关键技术点**:
- `dart:convert` 解析 SSE `data:` 事件
- `StreamBuilder<String>` 实时更新 UI
- 光标闪烁动画 (AnimatedOpacity)
- Markdown 增量渲染 (避免每个 token 重新渲染全部)

---

### 3.5 推送通知 (FCM)

```
用户退出 App → 后台任务完成
    │
    ▼
Backend: notification_service.py
    │
    ├── 1. 检查用户推送偏好设置
    ├── 2. 构建推送 Payload
    │       { title: "对话完成", body: "你的长文生成已完成", data: { conv_id: "xxx" } }
    ├── 3. 发送到 FCM / APNs
    │
    ▼
Flutter: firebase_messaging 插件
    ├── 前台: 本地通知 Toast
    ├── 后台/锁屏: 系统推送通知
    └── 点击通知: 跳转到对应会话
```

**推送场景**:
| 场景 | 触发条件 | 优先级 |
|:-----|:---------|:------:|
| 长文生成完成 | AI 回复超过 30 秒 | 高 |
| Key 余额不足 | 日预算消耗 > 80% | 中 |
| Key 全部失效 | 所有 Key 冷却/停用 | 高 |
| 新版本可用 | 后端版本更新 | 低 |

---

## 四、API 设计

### 4.1 核心端点

```
# === 认证 ===
POST   /api/v1/auth/register          # 注册
POST   /api/v1/auth/login             # 登录 → JWT
POST   /api/v1/auth/refresh           # 刷新 Token

# === 聊天 ===
POST   /api/v1/chat/completions       # 🔑 对话 (SSE 流式)
GET    /api/v1/chat/conversations      # 会话列表
GET    /api/v1/chat/conversations/{id} # 会话详情 (含消息)
POST   /api/v1/chat/conversations      # 创建会话 (指定预设)
DELETE /api/v1/chat/conversations/{id} # 删除会话
PATCH  /api/v1/chat/conversations/{id} # 更新会话 (标题/预设)

# === 预设/角色卡 ===
GET    /api/v1/presets                 # 预设列表
POST   /api/v1/presets/import          # 🔑 导入酒馆 JSON
GET    /api/v1/presets/{id}            # 预设详情
PUT    /api/v1/presets/{id}            # 更新预设
DELETE /api/v1/presets/{id}            # 删除预设
GET    /api/v1/presets/{id}/modules    # 获取模组列表 (可开关)
PATCH  /api/v1/presets/{id}/modules    # 批量更新模组开关

# === Token 池管理 ===
GET    /api/v1/keys                    # Key 列表 (脱敏显示)
POST   /api/v1/keys                    # 添加 Key
PUT    /api/v1/keys/{id}               # 更新 Key
DELETE /api/v1/keys/{id}               # 删除 Key
GET    /api/v1/keys/{id}/test          # 测试 Key 可用性

# === Token 用量统计 ===
GET    /api/v1/stats/usage             # 🔑 用量概览 (日/周/月)
GET    /api/v1/stats/usage/by-model    # 按模型统计
GET    /api/v1/stats/usage/by-key      # 按 Key 统计
GET    /api/v1/stats/usage/by-conversation  # 按会话统计
GET    /api/v1/stats/cost              # 费用统计

# === 推送 ===
POST   /api/v1/notifications/register  # 注册 FCM Token
PUT    /api/v1/notifications/preferences # 推送偏好设置
```

---

## 五、Flutter 页面设计

### 5.1 页面结构

```
┌─────────────────────────────────────────────┐
│            Bottom Navigation Bar             │
├──────┬──────┬──────┬──────┬────────────────┤
│ 💬   │ 🎭   │ 📊   │ ⚙️   │               │
│ 聊天  │ 角色  │ 统计  │ 设置  │               │
└──────┴──────┴──────┴──────┴────────────────┘

1. 聊天 Tab
   ├── 会话列表页 (最近对话, 搜索, 新建)
   └── 聊天详情页 (消息流, 流式打字, Markdown)

2. 角色 Tab
   ├── 角色卡画廊 (网格展示, 分类筛选)
   ├── 角色卡详情 (模组开关列表, 参数调整)
   └── 导入角色卡 (文件选择 / URL 导入)

3. 统计 Tab
   ├── Token 用量仪表盘 (日/周/月图表)
   ├── 费用摘要 (按模型/Key 分组)
   └── Key 状态概览 (健康/冷却/停用)

4. 设置 Tab
   ├── API Key 管理 (添加/测试/排序)
   ├── 安全设置 (E2E 加密开关/密钥管理)
   ├── 推送设置 (通知偏好)
   ├── 主题切换 (暗色/亮色)
   └── 关于 (版本/开源协议)
```

---

## 六、从 HiveMind 迁移清单

| 资产 | 来源 | 迁移方式 | 优先级 |
|:-----|:-----|:---------|:------:|
| `core/config.py` | HiveMind | 精简后复制 | P0 |
| `core/database.py` | HiveMind | 直接复用 | P0 |
| `core/security.py` | HiveMind | 复用 + 加 E2E | P0 |
| `core/exceptions.py` | HiveMind | 直接复用 | P0 |
| `core/logging.py` | HiveMind | 直接复用 | P0 |
| `api/routes/chat.py` (SSE) | HiveMind | 核心复用 | P0 |
| `services/ws_manager.py` | HiveMind | 直接复用 | P1 |
| `prompts/engine.py + loader.py` | HiveMind | 适配角色卡后复用 | P0 |
| `llm/router.py` | HiveMind | 完善 + 加 TokenPool | P0 |
| `llm/guardrails.py` | HiveMind | 直接复用 | P1 |
| `.agent/rules/*` | HiveMind | 加 Flutter rules | P0 |
| `.agent/workflows/*` | HiveMind | 适配 Flutter | P0 |
| `.agent/checks/*` | HiveMind | 直接复用 | P2 |

---

## 七、开发里程碑

| 阶段 | 内容 | 预估 |
|:-----|:-----|:----:|
| **M1: 骨架搭建** | Flutter 项目 + 后端骨架 + 迁移治理体系 + DB/Auth | 3 天 |
| **M2: 聊天核心** | SSE 流式 + 消息 CRUD + Flutter 聊天 UI + 打字效果 | 5 天 |
| **M3: 角色卡引擎** | 酒馆 JSON 导入解析 + 宏引擎 + 正则管道 + Prompt 组装 | 5 天 |
| **M4: Token 池** | Key 管理 + 负载均衡 + 限速 + 冷却 + 统计面板 | 4 天 |
| **M5: 安全与推送** | E2E 加密 + FCM 推送 + 通知偏好 | 3 天 |
| **M6: 打磨上线** | 主题/深色模式 + 性能优化 + 测试 + 部署 | 3 天 |

**总计: ~23 天**
