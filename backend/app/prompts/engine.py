"""
Prompt Engine — 四层 Prompt 组合引擎 (v3.0)。

职责:
    1. 加载 YAML 配置 (Layer 1: Base, Layer 2: Role)
    2. 渲染 Jinja2 模板 (Layer 3: Task)
    3. 注入运行时上下文 (Layer 4: Context)
    4. 缓存和版本管理
    5. 静态/动态分离 + Prompt Cache 优化 (v2.0)
    6. 进程级静态前缀缓存 (v3.0 新增)

架构:
    Layer 1 (Base)     → base/system.yaml, base/output_schemas.yaml
    Layer 1.5 (Eng)    → base/defensive_engineering.yaml
    Layer 2 (Role)     → agents/<agent_name>.yaml
    Layer 3 (Task)     → templates/<task_type>.j2
    Layer 4 (Context)  → 运行时注入 (messages, RAG results, memory)

Cache 优化 (v2.0, 借鉴 Claude Code):
    - 静态部分 (身份、安全、角色、工程约束) 在 CACHE_BOUNDARY 之前
    - 动态部分 (RAG 上下文、记忆、环境信息) 在 CACHE_BOUNDARY 之后
    - 静态部分的 hash 不变时可跨请求复用 prefix cache, 节省 15-25% token

进程级缓存 (v3.0):
    - 服务启动时，预渲染每个 agent 的静态前缀（Layer 1 + Layer 2），存在内存 dict 里
    - 请求时直接取预渲染好的静态前缀 + 拼接动态部分
    - 两层收益:
      1. 本地: 跳过 YAML 加载 + Jinja2 渲染
      2. API 侧: 静态前缀字节级一致 → DeepSeek V4 前缀缓存 100% 命中

    为什么叫"进程级":
      - 缓存存在 Python 进程的内存里（dict），不依赖 Redis/Memcached
      - 进程重启时自动重建（因为 YAML 和模板文件没变，渲染结果也不变）
      - 多 worker 进程各自持有一份（内存占用极小，几十 KB）

使用:
    engine = PromptEngine()

    # 方式 1: 传统方式（兼容旧代码）
    prompt = engine.build_agent_prompt(agent_name="rag_agent", task="...", rag_context="...")

    # 方式 2: 缓存感知方式（推荐，最大化 API 侧缓存命中）
    messages = engine.build_cache_aware_messages(
        agent_name="rag_agent",
        task="查找关于机器学习的文档",
        rag_context="[Document 1] ...",
    )
    # messages 结构:
    # [
    #   {"role": "system", "content": "<静态前缀，字节级稳定>"},
    #   {"role": "user",   "content": "<动态部分: task + RAG + memory>"},
    # ]
"""

import hashlib
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader
from loguru import logger

PROMPT_DIR = Path(__file__).parent

# 静态/动态分离标记 — 此标记之前的内容可跨请求缓存
PROMPT_CACHE_BOUNDARY = "__HIVEMIND_PROMPT_CACHE_BOUNDARY__"


class PromptEngine:
    """
    Prompt 组合引擎 — 从分层配置构建完整的 System Prompt。

    设计理念:
        - YAML 定义 WHAT (角色、约束、格式)
        - Jinja2 定义 HOW (如何组合)
        - Python 定义 WHEN (运行时注入上下文)
    """

    def __init__(self, prompt_dir: Path = PROMPT_DIR) -> None:
        self._prompt_dir = prompt_dir
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(prompt_dir / "templates")),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # 缓存已加载的 YAML 配置
        self._config_cache: dict[str, dict[str, Any]] = {}

        # 预加载 Layer 1
        self._base = self._load_yaml("base", "system")
        self._schemas = self._load_yaml("base", "output_schemas")
        self._platform_kb = self._load_yaml("base", "platform_knowledge")
        self._defensive = self._load_yaml("base", "defensive_engineering")

        # ── v3.0: 进程级静态前缀缓存 ──────────────────────────────
        # key = agent_name (或 "supervisor", "reflection")
        # value = (static_prefix_str, blake2b_hash)
        self._static_prefix_cache: dict[str, tuple[str, str]] = {}
        self._warmup_static_prefixes()

        logger.info(f"PromptEngine v3.0 initialized (dir={prompt_dir})")

    # ============================================================
    #  v3.0: 进程级静态前缀缓存
    # ============================================================

    def _warmup_static_prefixes(self) -> None:
        """
        服务启动时预渲染所有已知 agent 的静态前缀。

        静态前缀 = Layer 1 (base) + Layer 1.5 (defensive) + Layer 2 (role)
        不包含任何动态内容（task, rag_context, memory 等）。

        这样做的目的:
        1. 请求时直接取字符串，跳过 YAML + Jinja2
        2. 字节级一致 → DeepSeek V4 前缀缓存 100% 命中
        """
        agents = self.list_available_agents()
        for agent_name in agents:
            self._build_and_cache_static_prefix(agent_name)

        # Supervisor 也预热
        self._build_and_cache_static_prefix("supervisor")

        logger.info(
            "🔥 [PromptEngine] Warmed up {} static prefixes: {}",
            len(self._static_prefix_cache),
            list(self._static_prefix_cache.keys()),
        )

    def _build_and_cache_static_prefix(self, agent_name: str) -> tuple[str, str]:
        """
        为指定 agent 构建静态前缀并缓存。

        静态前缀的内容:
        - 系统身份 (base/system.yaml)
        - 安全约束 (base/defensive_engineering.yaml)
        - 输出格式 (base/output_schemas.yaml)
        - 角色定义 (agents/<agent_name>.yaml)

        Returns:
            (static_prefix, hash)
        """
        if agent_name in self._static_prefix_cache:
            return self._static_prefix_cache[agent_name]

        role = self._load_yaml("agents", agent_name)
        if not role:
            role = {
                "role": f"You are {agent_name}, a helpful specialist agent.",
                "constraints": [],
            }

        # 用一个专门的静态模板渲染，不包含任何动态变量
        # 如果没有 static_prefix.j2，就用 base + role 的文本拼接
        try:
            template = self._jinja_env.get_template("static_prefix.j2")
            prefix = template.render(
                base=self._base,
                role=role,
                schemas=self._schemas,
                platform_kb=self._platform_kb,
                defensive=self._defensive,
            )
        except Exception:
            # 没有专门的静态模板，用简单拼接
            parts = []
            if self._base.get("identity"):
                parts.append(str(self._base["identity"]))
            if self._defensive.get("rules"):
                parts.append(str(self._defensive["rules"]))
            if role.get("role"):
                parts.append(str(role["role"]))
            if role.get("constraints"):
                constraints = role["constraints"]
                if isinstance(constraints, list):
                    parts.append("\n".join(f"- {c}" for c in constraints))
            if self._schemas.get("output_format"):
                parts.append(str(self._schemas["output_format"]))
            prefix = "\n\n".join(parts)

        prefix_hash = hashlib.blake2b(prefix.encode(), digest_size=16).hexdigest()
        self._static_prefix_cache[agent_name] = (prefix, prefix_hash)
        return prefix, prefix_hash

    def get_static_prefix(self, agent_name: str) -> tuple[str, str]:
        """
        获取 agent 的静态前缀（从进程缓存中取，O(1) 查找）。

        Returns:
            (static_prefix_str, blake2b_hash)
        """
        if agent_name not in self._static_prefix_cache:
            return self._build_and_cache_static_prefix(agent_name)
        return self._static_prefix_cache[agent_name]

    def build_cache_aware_messages(
        self,
        agent_name: str,
        task: str,
        rag_context: str = "",
        memory_context: str = "",
        tools_available: list[str] | None = None,
        user_message: str = "",
        language: str = "zh-CN",
    ) -> list[dict[str, str]]:
        """
        构建缓存感知的 messages 列表（v3.0 推荐方式）。

        将 prompt 拆成两条 message:
        1. system message = 静态前缀（字节级稳定，API 侧 100% 缓存命中）
        2. user message   = 动态部分（task + RAG + memory + 用户输入）

        这样 DeepSeek V4 的前缀缓存会自动命中 system message 部分，
        只对 user message 部分按 cache miss 计费。

        Args:
            agent_name:      Agent 名称
            task:            任务描述
            rag_context:     RAG 检索结果
            memory_context:  记忆上下文
            tools_available: 可用工具列表
            user_message:    用户原始输入（如果有的话）
            language:        语言

        Returns:
            [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
        """
        # 1. 静态前缀（从进程缓存取）
        static_prefix, prefix_hash = self.get_static_prefix(agent_name)

        # 2. 动态部分
        dynamic_parts = []
        if task:
            dynamic_parts.append(f"## 当前任务\n{task}")
        if rag_context:
            dynamic_parts.append(f"## 参考资料\n{rag_context}")
        if memory_context:
            dynamic_parts.append(f"## 相关记忆\n{memory_context}")
        if tools_available:
            tools_str = ", ".join(tools_available)
            dynamic_parts.append(f"## 可用工具\n{tools_str}")

        dynamic_content = "\n\n".join(dynamic_parts)

        # 如果有用户原始输入，追加到动态部分
        if user_message:
            dynamic_content = f"{dynamic_content}\n\n## 用户输入\n{user_message}"

        messages = [
            {"role": "system", "content": static_prefix},
            {"role": "user", "content": dynamic_content},
        ]

        logger.debug(
            "📝 [CacheAware] agent={} | prefix_hash={} | static={}chars | dynamic={}chars",
            agent_name,
            prefix_hash[:8],
            len(static_prefix),
            len(dynamic_content),
        )
        return messages

    # ============================================================
    #  公开 API — 构建各类 Prompt（兼容旧代码）
    # ============================================================

    def build_supervisor_prompt(
        self,
        agents: list[dict[str, str]],
        rag_context: str = "",
        memory_context: str = "",
        language: str = "zh-CN",
    ) -> str:
        """
        构建 Supervisor 路由 Prompt。

        Args:
            agents: 可用 Agent 列表, 每个 dict 包含 name 和 description
            rag_context: 当前 RAG 检索到的内容 (context_data)
            memory_context: 可选的记忆上下文
        """
        role = self._load_yaml("agents", "supervisor")

        prompt = self._render_template(
            "supervisor_routing.j2",
            base=self._base,
            role=role,
            schemas=self._schemas,
            agents=agents,
            rag_context=rag_context,
            memory_context=memory_context,
            language=language,
        )

        self._log_prompt("supervisor_routing", prompt)
        return prompt

    def build_agent_prompt(
        self,
        agent_name: str,
        task: str,
        rag_context: str = "",
        memory_context: str = "",
        tools_available: list[str] | None = None,
        prompt_variant: str = "default",
        language: str = "zh-CN",
    ) -> str:
        """
        构建 Agent 执行任务 Prompt。

        Args:
            agent_name: Agent 名称 (必须有对应的 agents/<name>.yaml)
            task: Supervisor 分配的具体任务描述
            rag_context: RAG 检索到的文档内容
            memory_context: 相关记忆片段
            tools_available: Agent 可用的工具列表
        """
        role = self._load_yaml("agents", agent_name)

        # 如果找不到 Agent 配置，使用通用默认值
        if not role:
            role = {
                "role": f"You are {agent_name}, a helpful specialist agent.",
                "constraints": [],
            }
            logger.warning(f"No prompt config found for agent: {agent_name}")

        prompt = self._render_template(
            "agent_task.j2",
            base=self._base,
            role=role,
            schemas=self._schemas,
            platform_kb=self._platform_kb,
            defensive=self._defensive,
            task=task,
            rag_context=rag_context,
            memory_context=memory_context,
            tools_available=tools_available or [],
            prompt_variant=prompt_variant,
            language=language,
        )

        self._log_prompt(f"agent_task:{agent_name}", prompt)
        return prompt

    def build_reflection_prompt(
        self,
        user_query: str,
        agent_name: str,
        agent_response: str,
        task_description: str,
        language: str = "zh-CN",
    ) -> str:
        """构建 Reflection 质量评估 Prompt。"""
        prompt = self._render_template(
            "reflection.j2",
            base=self._base,
            schemas=self._schemas,
            user_query=user_query,
            agent_name=agent_name,
            agent_response=agent_response,
            task_description=task_description,
            language=language,
        )

        self._log_prompt("reflection", prompt)
        return prompt

    def build_custom_prompt(
        self,
        template_name: str,
        **kwargs: Any,
    ) -> str:
        """
        使用自定义模板构建 Prompt。

        自动注入 base 和 schemas，其余变量由调用方传入。
        """
        prompt = self._render_template(
            template_name,
            base=self._base,
            schemas=self._schemas,
            **kwargs,
        )
        self._log_prompt(f"custom:{template_name}", prompt)
        return prompt

    # ============================================================
    #  配置查询
    # ============================================================

    def get_agent_config(self, agent_name: str) -> dict[str, Any]:
        """获取 Agent 的 YAML 配置 (用于读取 model_hint 等元数据)。"""
        return self._load_yaml("agents", agent_name)

    def get_model_hint(self, agent_name: str) -> str:
        """获取 Agent 建议使用的模型类型。"""
        config = self.get_agent_config(agent_name)
        return config.get("meta", {}).get("model_hint", "balanced")

    def list_available_agents(self) -> list[str]:
        """列出所有有 prompt 配置的 Agent。"""
        agents_dir = self._prompt_dir / "agents"
        if not agents_dir.exists():
            return []
        return [f.stem for f in agents_dir.glob("*.yaml") if f.stem != "__init__"]

    # ============================================================
    #  Prompt Cache 优化 (v2.0)
    # ============================================================

    def split_prompt_for_cache(self, prompt: str) -> tuple[str, str]:
        """
        将完整 prompt 按 CACHE_BOUNDARY 分割为静态和动态两部分。

        静态部分 (身份、安全、角色、工程约束) 可跨请求缓存。
        动态部分 (RAG 上下文、记忆、环境信息) 每次重算。

        Returns:
            (static_prefix, dynamic_suffix)
        """
        boundary = self._base.get("cache_boundary", PROMPT_CACHE_BOUNDARY)
        if boundary in prompt:
            parts = prompt.split(boundary, 1)
            return parts[0].rstrip(), parts[1].lstrip()
        return prompt, ""

    def get_static_prompt_hash(self, prompt: str) -> str:
        """
        计算静态部分的 hash, 用于 prefix cache 命中判断。

        如果 hash 不变, 说明静态部分没有变化, 可以复用缓存。
        """
        static, _ = self.split_prompt_for_cache(prompt)
        return hashlib.blake2b(static.encode(), digest_size=16).hexdigest()

    # ============================================================
    #  热更新
    # ============================================================

    def reload(self) -> None:
        """清除缓存，强制重新加载所有配置（含静态前缀缓存）。"""
        self._config_cache.clear()
        self._static_prefix_cache.clear()
        self._base = self._load_yaml("base", "system")
        self._schemas = self._load_yaml("base", "output_schemas")
        self._platform_kb = self._load_yaml("base", "platform_knowledge")
        self._defensive = self._load_yaml("base", "defensive_engineering")
        # 重新初始化 Jinja2 环境 (刷新模板缓存)
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(self._prompt_dir / "templates")),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        # 重新预热静态前缀
        self._warmup_static_prefixes()
        logger.info("🔄 PromptEngine v3.0 reloaded — all caches cleared and re-warmed")

    # ============================================================
    #  内部方法
    # ============================================================

    def _load_yaml(self, sub_dir: str, name: str) -> dict[str, Any]:
        """加载并缓存 YAML 配置。"""
        cache_key = f"{sub_dir}/{name}"

        if cache_key in self._config_cache:
            return self._config_cache[cache_key]

        file_path = self._prompt_dir / sub_dir / f"{name}.yaml"
        if not file_path.exists():
            logger.warning(f"Prompt YAML not found: {file_path}")
            return {}

        try:
            with open(file_path, encoding="utf-8", errors="replace") as f:
                data = yaml.safe_load(f) or {}
            self._config_cache[cache_key] = data
            return data
        except Exception as e:
            logger.error(f"Failed to load {file_path}: {e}")
            return {}

    def _render_template(self, template_name: str, **kwargs: Any) -> str:
        """渲染 Jinja2 模板。"""
        try:
            template = self._jinja_env.get_template(template_name)
            return template.render(**kwargs)
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {e}")
            return f"[PROMPT RENDER ERROR: {e}]"

    def _log_prompt(self, label: str, prompt: str) -> None:
        """记录 Prompt 的摘要信息 (用于调试和追踪)。"""
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
        lines = prompt.strip().split("\n")
        logger.debug(f"📝 Prompt [{label}] | hash={prompt_hash} | lines={len(lines)} | chars={len(prompt)}")


# ============================================================
#  全局单例
# ============================================================
prompt_engine = PromptEngine()
