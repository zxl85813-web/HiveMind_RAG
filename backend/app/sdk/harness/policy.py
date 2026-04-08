from abc import ABC, abstractmethod
from typing import Any, Dict, List
from dataclasses import dataclass

@dataclass
class PolicyResult:
    passed: bool
    message: str | None = None
    level: str = "error"  # "error" | "warning"

class HarnessPolicy(ABC):
    """
    所有 Harness 拦截策略的基类。
    """
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def validate(self, context: Dict[str, Any]) -> PolicyResult:
        """
        执行策略校验。
        context 包含: Proposed Code, Change ID, User context 等。
        """
        pass
