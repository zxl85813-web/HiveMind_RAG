"""
Prompt Engine — 四层 Prompt 组合引擎 (V2 - 架构升级版)。

职责:
    1. 加载 YAML 配置 (Layer 1: Base, Layer 2: Role)
    2. 自动进行「正向与反向提示词 (Positive & Negative Constraints)」拆解
    3. 根据 LLM 模型家族 (Claude/Gemini -> XML 风格, GPT/DeepSeek -> Markdown 风格) 动态调整 Prompt 物理结构
    4. 评估运行时 Context 长度，启用「双端布局 (Double-ended Layout)」以抵御 "Lost in the Middle" 效应
    5. 缓存和版本管理

使用:
    engine = PromptEngine()
    prompt = engine.build_agent_prompt(
        agent_name="rag_agent",
        task="...",
        rag_context="...",
        model_name="claude-3-5-sonnet"
    )
"""

import hashlib
import json
from pathlib import Path
from typing import Any, List, Dict, Tuple

import yaml
from jinja2 import Environment, FileSystemLoader

from loguru import logger

PROMPT_DIR = Path(__file__).parent


class PromptEngine:
    """
    Prompt 组合引擎 — 从分层配置构建高品质、动态适配的 System Prompt。
    
    升级特性：
        - **模型感知适配**：自动为 Claude/Gemini 使用原生 XML 隔离墙，为 GPT/DeepSeek 使用经典 Markdown 分组。
        - **抗 Lost in the Middle**：当上下文过大时，自动将核心约束与 Output Schema 复制到 prompt 的首尾两端。
        - **正向/反向提示词自动拆分**：智能提炼 Do's 和 Don'ts。
        - **链式集成支持**：预留 CoT (思考标签) 注入。
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
        self._config_cache: Dict[str, Dict[str, Any]] = {}

        # 预加载 Layer 1
        self._base = self._load_yaml("base", "system")
        self._schemas = self._load_yaml("base", "output_schemas")
        self._platform_kb = self._load_yaml("base", "platform_knowledge")

        logger.info(f"🚀 PromptEngine V2 (Advanced Archetype) initialized (dir={prompt_dir})")

    # ============================================================
    #  核心分析与自适应层
    # ============================================================

    def _detect_model_style(self, model_name: str, agent_name: str = "") -> str:
        """
        根据模型名称或 Agent 的 model_hint 检测适配的 Prompt 风格。
        
        返回:
            "xml": 适用于 Claude 3/3.5, Gemini 1.5/2.0 等对 XML 标签极其敏感的模型
            "markdown": 适用于 GPT-4, DeepSeek 等偏好经典 Markdown 的模型
        """
        target = model_name.lower() if model_name else ""
        if not target and agent_name:
            hint = self.get_model_hint(agent_name)
            target = hint.lower() if hint else ""

        # 匹配 XML 风格模型
        xml_families = ["claude", "gemini", "anthropic", "google", "reasoning"]
        if any(fam in target for fam in xml_families):
            return "xml"
        
        # 默认使用通用 markdown 风格
        return "markdown"

    def _estimate_context_tier(self, rag_context: str, memory_context: str) -> str:
        """
        计算 Context 长度层级，用来防范 "Lost in the Middle" 效应。
        
        规则：
            - 大于 6000 字符 (约 1500 tokens) 判定为 "large" 级别，激活双端冗余机制。
            - 否则判定为 "normal" 级别。
        """
        total_chars = len(rag_context or "") + len(memory_context or "")
        return "large" if total_chars > 6000 else "normal"

    def _split_constraints(self, safety_rules: List[str], agent_constraints: List[str]) -> Tuple[List[str], List[str]]:
        """
        将全局安全规则和 Agent 特定约束，分类拆解为正向提示词(Do's)和反向提示词(Don'ts)。
        """
        positives = []
        negatives = []

        # 反向提示词特征词
        negative_indicators = {
            "never", "do not", "avoid", "must not", "don't", "ignore", "fabricate", 
            "destructive", "harmful", "illegal", "unethical", "bypass", "refuse",
            "不能", "不要", "绝对不能", "避免", "禁止", "严禁"
        }

        all_rules = list(safety_rules or []) + list(agent_constraints or [])
        for rule in all_rules:
            rule_clean = rule.strip()
            if not rule_clean:
                continue
            
            rule_lower = rule_clean.lower()
            if any(ind in rule_lower for ind in negative_indicators):
                negatives.append(rule_clean)
            else:
                positives.append(rule_clean)

        return positives, negatives

    def _format_section(self, title: str, content: str, style: str, tag_name: str) -> str:
        """
        通用区块格式化器：根据风格输出 XML 或 Markdown 隔离墙。
        """
        if not content or not content.strip():
            return ""

        if style == "xml":
            return f"<{tag_name}>\n{content.strip()}\n</{tag_name}>"
        else:
            return f"## {title}\n{content.strip()}"

    # ============================================================
    #  公开 API — 构建各类自适应 Prompt
    # ============================================================

    def build_agent_prompt(
        self,
        agent_name: str,
        task: str,
        rag_context: str = "",
        memory_context: str = "",
        tools_available: List[str] | None = None,
        model_name: str = "",
    ) -> str:
        """
        构建 Agent 执行任务 System Prompt (V2 自适应架构)。
        
        实现了：
            1. 模型风格自适应 (XML vs Markdown)
            2. 正反向提示词分类隔离
            3. 双端抗遗忘布局 (Lost in the Middle mitigation)
        """
        role_config = self._load_yaml("agents", agent_name)

        if not role_config:
            role_config = {
                "role": f"You are {agent_name}, a helpful specialist agent.",
                "constraints": [],
                "personality": []
            }
            logger.warning(f"No prompt config found for agent: {agent_name}")

        # 1. 参数分析与策略匹配
        style = self._detect_model_style(model_name, agent_name)
        context_tier = self._estimate_context_tier(rag_context, memory_context)
        
        # 2. 正反向约束提炼
        safety_rules = self._base.get("safety", [])
        agent_constraints = role_config.get("constraints", [])
        positives, negatives = self._split_constraints(safety_rules, agent_constraints)

        # 3. 基础板块物料准备
        identity_str = self._base.get("identity", "You are part of HiveMind.")
        role_str = role_config.get("role", "")
        
        # 组装正反向约束段
        pos_str = "\n".join(f"- {p}" for p in positives)
        neg_str = "\n".join(f"- {n}" for n in negatives)
        
        schema_str = self._schemas.get("agent_response", "")

        # 4. 动态编排 (Double-Ended Layout / 双端抗遗忘)
        prompt_parts = []

        # [头部区] Identity & Persona
        prompt_parts.append(self._format_section("Identity", identity_str, style, "identity"))
        prompt_parts.append(self._format_section("Your Role", role_str, style, "role"))
        
        # [头部区] 约束预读与格式锚定
        prompt_parts.append(self._format_section("Guidelines (Do's)", pos_str, style, "guidelines"))
        prompt_parts.append(self._format_section("Anti-Patterns (Don'ts)", neg_str, style, "anti_patterns"))
        
        if context_tier == "large":
            # 如果是大上下文，头部先打一个 Output Schema 预防针 (Pre-conditioning)
            prompt_parts.append(self._format_section("Expected Output Format", schema_str, style, "output_format"))

        # [中部数据区] (容易被 LLM 注意力遗忘的区域)
        # 注入平台内置知识
        if self._platform_kb:
            kb_lines = [self._platform_kb.get("overview", "")]
            for feat in self._platform_kb.get("features", []):
                f_name = feat.get("name", "")
                f_path = feat.get("path", "")
                f_desc = feat.get("description", "")
                kb_lines.append(f"- **{f_name}** (`{f_path}`): {f_desc}")
            prompt_parts.append(self._format_section("Platform Features", "\n".join(kb_lines), style, "platform_features"))

        # 注入 RAG 检索到的文档
        if rag_context:
            rag_instruction = (
                "The following documents were retrieved from the knowledge base.\n"
                "Use them as your PRIMARY source of truth. Append citations like [idx] where applicable.\n\n"
                f"{rag_context}"
            )
            prompt_parts.append(self._format_section("Retrieved Documents", rag_instruction, style, "documents"))

        # 注入记忆
        if memory_context:
            prompt_parts.append(self._format_section("Relevant Memory", memory_context, style, "memory"))

        # [尾部重点强化区] Task & Tools
        task_str = f"Your current task is: {task}"
        if tools_available:
            tool_list = "\n".join(f"- `{t}`" for t in tools_available)
            task_str += f"\n\nYou have access to these tools:\n{tool_list}\nUse them when helpful."
        prompt_parts.append(self._format_section("Current Task", task_str, style, "task"))

        # [双端布局 - 尾部重复]
        # 重复最关键的安全与反向约束，防止被大量 context 稀释
        if context_tier == "large":
            reinforce_neg = (
                "CRITICAL AUDIT: You must review your reasoning against these strict Anti-Patterns before replying:\n"
                f"{neg_str}"
            )
            prompt_parts.append(self._format_section("Anti-Patterns Audit", reinforce_neg, style, "anti_patterns_reinforce"))

        # 强制格式约束放尾部
        prompt_parts.append(self._format_section("Final Output Format", schema_str, style, "output_format"))

        # [CoT 推理引导]
        if style == "xml":
            cot_directive = (
                "Before rendering your JSON/Markdown output, you MUST map out your analysis "
                "inside <thinking> tags. Analyze: 1) What the user expects, 2) Which guidelines apply, "
                "3) Any safety boundary violated. Then, output your structured answer."
            )
            prompt_parts.append(self._format_section("Reasoning Process", cot_directive, style, "thinking_instructions"))

        # 5. 组合与日志记录
        final_prompt = "\n\n".join(part for part in prompt_parts if part)
        self._log_prompt(f"agent_task:{agent_name} [{style}] [{context_tier}]", final_prompt)
        return final_prompt

    def build_supervisor_prompt(
        self,
        agents: List[Dict[str, str]],
        memory_context: str = "",
        model_name: str = "",
    ) -> str:
        """
        构建 Swarm Supervisor 路由决策 Prompt (V2 自适应升级)。
        """
        role_config = self._load_yaml("agents", "supervisor")
        style = self._detect_model_style(model_name, "supervisor")
        
        # 提取基础块
        identity_str = self._base.get("identity", "")
        role_str = role_config.get("role", "You route requests.")
        schema_str = self._schemas.get("routing_decision", "")

        # 组装代理列表
        agent_lines = []
        for agent in agents:
            agent_lines.append(f"- **{agent['name']}**: {agent['description']}")
        agents_str = "\n".join(agent_lines)

        # 组装路由规范
        routing_logic = (
            "1. Analyze Intent: Determine user's query direction.\n"
            "2. Self-RAG Check: If query needs internal knowledge, route to 'retrieval'.\n"
            "3. Loop Management: If an agent hit a wall, route to others or finish.\n"
            "4. Platform Match: If matching platform intents, delegate immediately."
        )

        prompt_parts = []
        prompt_parts.append(self._format_section("Identity", identity_str, style, "identity"))
        prompt_parts.append(self._format_section("Your Role", role_str, style, "role"))
        prompt_parts.append(self._format_section("Available Agents", agents_str, style, "agents"))
        prompt_parts.append(self._format_section("Routing Logic", routing_logic, style, "routing_rules"))
        
        if memory_context:
            prompt_parts.append(self._format_section("Context & Memory", memory_context, style, "memory"))
            
        prompt_parts.append(self._format_section("Output Format Schema", schema_str, style, "output_format"))

        if style == "xml":
            cot_directive = (
                "You MUST analyze the user query step by step inside <thinking> tags first, "
                "determining if 'retrieval' or a specialist is required. Then output the routing JSON."
            )
            prompt_parts.append(self._format_section("Routing CoT", cot_directive, style, "thinking_instructions"))

        final_prompt = "\n\n".join(part for part in prompt_parts if part)
        self._log_prompt(f"supervisor_routing [{style}]", final_prompt)
        return final_prompt

    def build_reflection_prompt(
        self,
        user_query: str,
        agent_name: str,
        agent_response: str,
        task_description: str,
        model_name: str = "",
    ) -> str:
        """
        构建 Reflection 质量检查 Prompt (V2 自适应升级)。
        """
        style = self._detect_model_style(model_name, "reflection")
        schema_str = self._schemas.get("reflection_result", "")

        context_str = (
            f"- **User's Original Query**: {user_query}\n"
            f"- **Task Given to Agent**: {task_description}\n"
            f"- **Responding Agent**: {agent_name}"
        )

        prompt_parts = []
        prompt_parts.append(self._format_section("Identity", self._base.get("identity", ""), style, "identity"))
        prompt_parts.append(self._format_section("Your Role", "You are the Quality Reviewer of the HiveMind system.", style, "role"))
        prompt_parts.append(self._format_section("Evaluation Context", context_str, style, "context"))
        prompt_parts.append(self._format_section("Agent's Response", f"```\n{agent_response}\n```", style, "agent_output"))
        
        criteria = (
            "1. Correctness: Is the response accurate?\n"
            "2. Completeness: Did the agent fully address the task?\n"
            "3. Safety: Are anti-patterns successfully avoided?"
        )
        prompt_parts.append(self._format_section("Evaluation Criteria", criteria, style, "criteria"))
        prompt_parts.append(self._format_section("Output Format Schema", schema_str, style, "output_format"))

        final_prompt = "\n\n".join(part for part in prompt_parts if part)
        self._log_prompt(f"reflection [{style}]", final_prompt)
        return final_prompt

    def build_custom_prompt(
        self,
        template_name: str,
        **kwargs: Any,
    ) -> str:
        """使用自定义模板构建 Prompt (保留向后兼容性)。"""
        prompt = self._render_template(
            template_name,
            base=self._base,
            schemas=self._schemas,
            **kwargs,
        )
        self._log_prompt(f"custom:{template_name}", prompt)
        return prompt

    # ============================================================
    #  底座及配置管理
    # ============================================================

    def get_agent_config(self, agent_name: str) -> dict[str, Any]:
        """获取 Agent 的 YAML 配置。"""
        return self._load_yaml("agents", agent_name)

    def get_model_hint(self, agent_name: str) -> str:
        """获取 Agent 建议使用的模型类型。"""
        config = self.get_agent_config(agent_name)
        return config.get("meta", {}).get("model_hint", "balanced")

    def list_available_agents(self) -> List[str]:
        """列出所有有 prompt 配置的 Agent。"""
        agents_dir = self._prompt_dir / "agents"
        if not agents_dir.exists():
            return []
        return [
            f.stem for f in agents_dir.glob("*.yaml")
            if f.stem != "__init__"
        ]

    def reload(self) -> None:
        """清除缓存，强制重新加载所有配置。"""
        self._config_cache.clear()
        self._base = self._load_yaml("base", "system")
        self._schemas = self._load_yaml("base", "output_schemas")
        self._platform_kb = self._load_yaml("base", "platform_knowledge")
        
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(self._prompt_dir / "templates")),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        logger.info("🔄 PromptEngine configurations reloaded — all caches cleared")

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
            with open(file_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            self._config_cache[cache_key] = data
            return data
        except Exception as e:
            logger.error(f"Failed to load {file_path}: {e}")
            return {}

    def _render_template(self, template_name: str, **kwargs: Any) -> str:
        """渲染 Jinja2 模板 (用于基础渲染)。"""
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
        logger.debug(
            f"📝 Prompt [{label}] | "
            f"hash={prompt_hash} | "
            f"lines={len(lines)} | "
            f"chars={len(prompt)}"
        )


# ============================================================
#  全局单例
# ============================================================
prompt_engine = PromptEngine()
