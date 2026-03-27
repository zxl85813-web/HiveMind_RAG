"""
Prompt Engine — 四层 Prompt 组合引擎。

职责:
    1. 加载 YAML 配置 (Layer 1: Base, Layer 2: Role)
    2. 渲染 Jinja2 模板 (Layer 3: Task)
    3. 注入运行时上下文 (Layer 4: Context)
    4. 缓存和版本管理

架构:
    Layer 1 (Base)     → base/system.yaml, base/output_schemas.yaml
    Layer 2 (Role)     → agents/<agent_name>.yaml
    Layer 3 (Task)     → templates/<task_type>.j2
    Layer 4 (Context)  → 运行时注入 (messages, RAG results, memory)

使用:
    engine = PromptEngine()

    # 生成 Supervisor 路由 Prompt
    prompt = engine.build_supervisor_prompt(
        agents=[...],
        memory_context="用户之前问过..."
    )

    # 生成 Agent 执行 Prompt
    prompt = engine.build_agent_prompt(
        agent_name="rag_agent",
        task="查找关于机器学习的文档",
        rag_context="[Document 1] ...",
    )
"""

import hashlib
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader
from loguru import logger

PROMPT_DIR = Path(__file__).parent


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

        logger.info(f"PromptEngine initialized (dir={prompt_dir})")

    # ============================================================
    #  公开 API — 构建各类 Prompt
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
    #  热更新
    # ============================================================

    def reload(self) -> None:
        """清除缓存，强制重新加载所有配置。"""
        self._config_cache.clear()
        self._base = self._load_yaml("base", "system")
        self._schemas = self._load_yaml("base", "output_schemas")
        # 重新初始化 Jinja2 环境 (刷新模板缓存)
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(self._prompt_dir / "templates")),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        logger.info("🔄 PromptEngine reloaded — all caches cleared")

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
