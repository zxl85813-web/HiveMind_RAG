import re
from typing import Any, Dict
from .policy import HarnessPolicy, PolicyResult

class SecuritySentinelPolicy(HarnessPolicy):
    """
    检查代码中是否包含危险的系统调用或模块引入。
    """
    FORBIDDEN_KEYWORDS = [
        r"import\s+subprocess", r"subprocess\.",
        r"eval\(", r"exec\(", r"pty\."
    ]

    @property
    def name(self) -> str:
        return "SecuritySentinel"

    async def validate(self, context: Dict[str, Any]) -> PolicyResult:
        content = context.get("content", "")
        for pattern in self.FORBIDDEN_KEYWORDS:
            if re.search(pattern, content):
                return PolicyResult(
                    passed=False,
                    message=f"Harness [SecuritySentinel]: Forbidden keyword/module detected: '{pattern}'. Change blocked."
                )
        return PolicyResult(passed=True)

class HiveConformancePolicy(HarnessPolicy):
    """
    强制执行 HIVE.md 中规定的全局工程与架构红线。
    """
    @property
    def name(self) -> str:
        return "HiveConformance"

    async def validate(self, context: Dict[str, Any]) -> PolicyResult:
        content = context.get("content", "")
        
        # 红线 1: 禁止使用 print() (对齐 HIVE.md)
        if re.search(r"\bprint\(", content):
            return PolicyResult(
                passed=False, 
                message="HIVE-REDLINE: Usage of 'print()' is forbidden. Use app.sdk.core.logging instead."
            )

        # 红线 2: 强制 Async I/O (对齐 HIVE.md)
        if "time.sleep(" in content or "requests.get(" in content:
             return PolicyResult(
                 passed=False, 
                 message="HIVE-REDLINE: Synchronous blocking calls (time.sleep/requests) detected. Use asyncio/httpx equivalent."
             )

        # 红线 3: Service 类命名规范
        if "class " in content and "Service" in content and "@register_component" not in content:
             return PolicyResult(
                 passed=False,
                 message="HIVE-REDLINE: Service classes must be registered using @register_component decorator."
             )

        return PolicyResult(passed=True)
