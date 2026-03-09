import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TraceStep:
    name: str
    type: str  # 'agent', 'tool', 'retrieval', 'llm'
    status: str = "success"
    input: Any = None
    output: Any = None
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def complete(self, output: Any = None, status: str = "success"):
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.output = output
        self.status = status


class ChatTracer:
    def __init__(self, request_id: str = None):
        self.request_id = request_id or str(uuid.uuid4())
        self.steps: list[TraceStep] = []
        self.start_time = time.time()

    def start_step(
        self, name: str, step_type: str, input_data: Any = None, metadata: dict[str, Any] = None
    ) -> TraceStep:
        step = TraceStep(name=name, type=step_type, input=input_data, metadata=metadata or {})
        self.steps.append(step)
        return step

    def get_trace_json(self) -> str:
        return json.dumps([asdict(s) for s in self.steps], ensure_ascii=False)

    def add_quick_step(self, name: str, output: str, step_type: str = "info", metadata: dict[str, Any] = None):
        """Utility for simple logging style steps"""
        step = TraceStep(name=name, type=step_type, output=output, metadata=metadata or {})
        step.complete(output=output)
        self.steps.append(step)
