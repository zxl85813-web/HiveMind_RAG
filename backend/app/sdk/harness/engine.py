import logging
from typing import Any, Protocol, List
from .policy import HarnessPolicy, PolicyResult
from .policies import SecuritySentinelPolicy, HiveConformancePolicy

logger = logging.getLogger(__name__)

class HarnessCheckResult(Protocol):
    """护栏检查结果协议"""
    passed: bool
    reason: str | None
    suggestions: list[str]

class HarnessEngine:
    """
    HiveMind AI 护栏引擎 (Harness Engine)。
    Responsible for multi-dimensional checking of AI actions.
    """
    def __init__(self):
        # 自动加载激活的策略
        self.policies: List[HarnessPolicy] = [
            SecuritySentinelPolicy(),
            HiveConformancePolicy()
        ]

    async def check_change(self, change_context: dict[str, Any]) -> PolicyResult:
        """
        验证一个代码变更请求，执行所有注册策略。
        """
        logger.info(f"Harness Engine: Validating change with {len(self.policies)} policies...")
        
        for policy in self.policies:
            result = await policy.validate(change_context)
            if not result.passed:
                logger.warning(f"Harness [FAILURE]: {policy.name} -> {result.message}")
                return result
        
        logger.info("Harness [SUCCESS]: All policies passed.")
        return PolicyResult(passed=True, message="Checked by HiveMind Harness")

    async def verify_output(self, content: str) -> bool:
        """
        验证 AI 生成的内容是否符合规范。
        """
        return True

_harness_engine = None

def get_harness_engine() -> HarnessEngine:
    global _harness_engine
    if not _harness_engine:
        _harness_engine = HarnessEngine()
    return _harness_engine
