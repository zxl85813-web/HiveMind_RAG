"""
Computational Sensors — M8.0.2
==============================
确定性、毫秒级、零 LLM 成本的输出验证。

每个 Sensor 实现 HarnessPolicy 接口，但 check_type="computational"。
"""

from __future__ import annotations

import ast
import json
import re
from typing import Any

from .policy import HarnessPolicy, PolicyResult


class ASTValidationSensor(HarnessPolicy):
    """
    对包含 Python 代码块的 Agent 输出做 ast.parse() 验证。
    仅在 output_type == "code" 或内容包含 ```python 代码块时触发。
    """

    @property
    def name(self) -> str:
        return "ASTValidation"

    @property
    def default_level(self) -> str:
        return "error"  # 语法错误是硬性失败

    async def validate(self, context: dict[str, Any]) -> PolicyResult:
        content: str = context.get("content", "")
        output_type: str = context.get("output_type", "text")

        # 提取代码块
        code_blocks = self._extract_python_blocks(content)

        if not code_blocks and output_type != "code":
            return PolicyResult(passed=True, check_type="computational")

        # 如果是纯代码输出（没有 markdown 包裹），整体当作代码
        if not code_blocks and output_type == "code":
            code_blocks = [content]

        errors = []
        for i, block in enumerate(code_blocks):
            try:
                ast.parse(block)
            except SyntaxError as e:
                errors.append(f"Block {i+1}: {e.msg} (line {e.lineno})")

        if errors:
            return PolicyResult(
                passed=False,
                message=f"AST validation failed: {'; '.join(errors)}",
                level=self.default_level,
                check_type="computational",
                details={"errors": errors, "block_count": len(code_blocks)},
            )

        return PolicyResult(
            passed=True,
            check_type="computational",
            details={"block_count": len(code_blocks)},
        )

    @staticmethod
    def _extract_python_blocks(text: str) -> list[str]:
        """从 Markdown 中提取 ```python ... ``` 代码块。"""
        pattern = r"```(?:python|py)?\s*\n(.*?)```"
        return [m.group(1) for m in re.finditer(pattern, text, re.DOTALL)]


class JSONSchemaSensor(HarnessPolicy):
    """
    对 ReviewerAgent 等输出 JSON 的 Agent 做结构验证。
    仅在 output_type == "json" 或内容包含 JSON 代码块时触发。
    """

    # ReviewerAgent 的预期字段
    REVIEWER_REQUIRED_FIELDS = {"risk_level", "findings", "requires_replan"}

    @property
    def name(self) -> str:
        return "JSONSchemaValidation"

    @property
    def default_level(self) -> str:
        return "warning"  # JSON 格式问题是 warning，不阻断

    async def validate(self, context: dict[str, Any]) -> PolicyResult:
        content: str = context.get("content", "")
        agent_name: str = context.get("agent_name", "")
        output_type: str = context.get("output_type", "text")

        if output_type != "json" and "HVM-Reviewer" not in agent_name:
            return PolicyResult(passed=True, check_type="computational")

        # 尝试解析 JSON
        json_str = self._extract_json(content)
        if not json_str:
            return PolicyResult(passed=True, check_type="computational")

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            return PolicyResult(
                passed=False,
                message=f"JSON parse error: {e.msg} (pos {e.pos})",
                level=self.default_level,
                check_type="computational",
            )

        # 对 ReviewerAgent 检查必需字段
        if "Reviewer" in agent_name and isinstance(data, dict):
            missing = self.REVIEWER_REQUIRED_FIELDS - set(data.keys())
            if missing:
                return PolicyResult(
                    passed=False,
                    message=f"Reviewer JSON missing fields: {missing}",
                    level="warning",
                    check_type="computational",
                    details={"missing_fields": list(missing)},
                )

        return PolicyResult(passed=True, check_type="computational")

    @staticmethod
    def _extract_json(text: str) -> str | None:
        """尝试从文本中提取 JSON 内容。"""
        # 先尝试整体解析
        stripped = text.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            return stripped

        # 尝试从 ```json 代码块提取
        match = re.search(r"```json?\s*\n(.*?)```", text, re.DOTALL)
        if match:
            return match.group(1).strip()

        return None


class IncompleteCodeSensor(HarnessPolicy):
    """
    检测 Agent 输出中的未完成标记。
    这些标记表明 Agent "偷懒"了，输出不完整。
    """

    INCOMPLETE_PATTERNS = [
        (r"\bTODO\b", "TODO marker"),
        (r"\bFIXME\b", "FIXME marker"),
        (r"\bHACK\b", "HACK marker"),
        (r"^\s*pass\s*$", "bare pass statement"),
        (r"^\s*\.\.\.\s*$", "ellipsis placeholder"),
        (r"#\s*implement\s*(this|here|later)", "implement-later comment"),
        (r"raise\s+NotImplementedError", "NotImplementedError"),
    ]

    @property
    def name(self) -> str:
        return "IncompleteCodeDetection"

    @property
    def default_level(self) -> str:
        return "warning"  # 未完成标记是 warning，不阻断

    async def validate(self, context: dict[str, Any]) -> PolicyResult:
        content: str = context.get("content", "")
        output_type: str = context.get("output_type", "text")

        # 只对代码类输出检查
        if output_type not in ("code", "json") and "```" not in content:
            return PolicyResult(passed=True, check_type="computational")

        found = []
        for pattern, label in self.INCOMPLETE_PATTERNS:
            matches = re.findall(pattern, content, re.MULTILINE | re.IGNORECASE)
            if matches:
                found.append(f"{label} (×{len(matches)})")

        if found:
            return PolicyResult(
                passed=False,
                message=f"Incomplete code detected: {', '.join(found)}",
                level=self.default_level,
                check_type="computational",
                details={"markers": found},
            )

        return PolicyResult(passed=True, check_type="computational")
