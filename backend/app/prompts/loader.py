"""
Prompt 加载器 — 统一管理系统提示词。

支持:
1. YAML 格式配置 (PromptConfig): 用于定义 Agent 的角色、风格、约束。
2. Jinja2 模板 (Template): 用于动态生成 Prompt (如插入用户问题、RAG 上下文)。

目录结构:
- base/       : 通用 system prompt (如 "你是一个 helpful assistant")
- agents/     : 各 Agent 专用 prompt (如 "rag_agent.yaml")
- templates/  : 动态模板 (如 "reflection.j2")

参见: REGISTRY.md > 后端 > prompts
"""

from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader

from app.core.logging import logger

# 当前目录
PROMPT_DIR = Path(__file__).parent


class PromptLoader:
    """Prompt 资源加载器 (单例模式推荐)。"""

    def __init__(self, prompt_dir: Path = PROMPT_DIR):
        self.prompt_dir = prompt_dir
        self.jinja_env = Environment(
            loader=FileSystemLoader(searchpath=prompt_dir / "templates"),
            autoescape=False,  # Prompt 不是 HTML，不需要转义
        )

    def load_config(self, name: str, sub_dir: str = "base") -> dict[str, Any]:
        """
        加载 YAML 格式的 Prompt 配置。

        Args:
            name: 文件名 (不含后缀), 如 "main_system"
            sub_dir: 子目录, 默认为 "base"

        Returns:
            配置字典
        """
        file_path = self.prompt_dir / sub_dir / f"{name}.yaml"
        if not file_path.exists():
            logger.warning(f"Prompt config not found: {file_path}")
            return {}

        try:
            with open(file_path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load prompt config {file_path}: {e}")
            return {}

    def render_template(self, template_name: str, **kwargs: Any) -> str:
        """
        渲染 Jinja2 模板。

        Args:
            template_name: 模板文件名 (含后缀), 如 "reflection.j2"
            kwargs: 模板变量

        Returns:
            渲染后的 Prompt 字符串
        """
        try:
            template = self.jinja_env.get_template(template_name)
            return template.render(**kwargs)
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {e}")
            return ""


# 全局实例
prompt_loader = PromptLoader()
