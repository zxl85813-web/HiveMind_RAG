"""
Unified Grader Architecture — 统一评估器体系

分层设计:
  BaseGrader          → 抽象基类，定义评分协议
  ├── FaithfulnessGrader   → 忠实度（逐句 claim 验证）
  ├── RelevanceGrader      → 答案相关性（逆向问题生成）
  ├── CorrectnessGrader    → 答案正确性（与 GT 事实对比）
  ├── ContextGrader        → 上下文质量（精确度 + 召回率）
  └── AssertionLayer       → 硬规则断言（所有 Grader 共享）

设计原则:
  1. 每个 Grader 独立 Prompt，避免认知负荷过重
  2. 强制 Chain-of-Thought 推理，先分析再评分
  3. 支持多次采样 + 置信度计算
  4. 硬规则断言作为最后防线
"""

from .base import BaseGrader, GradeResult
from .faithfulness import FaithfulnessGrader
from .relevance import RelevanceGrader
from .correctness import CorrectnessGrader
from .context import ContextPrecisionGrader, ContextRecallGrader
from .instruction import InstructionFollowingGrader

__all__ = [
    "BaseGrader",
    "GradeResult",
    "FaithfulnessGrader",
    "RelevanceGrader",
    "CorrectnessGrader",
    "ContextPrecisionGrader",
    "ContextRecallGrader",
    "InstructionFollowingGrader",
]
