"""
Verification test for Unified Logging Protocol.
Validates trace ID propagation, JSON schema compliance, and middleware integration.
"""

import json
import sys
import uuid
import asyncio
from datetime import datetime
from io import StringIO
from pathlib import Path
from contextvars import ContextVar

import pytest
import loguru

# Windows console UTF-8 fix for standard outputs
try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, Exception):
    pass

# Ensure backend path is in sys.path
BASE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE / "backend"))

from app.schemas.monitor import UnifiedLog, Platform, EventCategory, LogLevel
from app.core.logging import trace_id_var, get_trace_logger

# =============================================================================
# [LOG-01] Pydantic Schema Validation
# =============================================================================

class TestUnifiedLogSchema:
    def test_valid_log_accepted(self):
        log = UnifiedLog(
            ts=datetime.utcnow(),
            level=LogLevel.INFO,
            trace_id=str(uuid.uuid4()),
            platform=Platform.BE,
            category=EventCategory.SYSTEM,
            module="TestRunner",
            action="test_start",
            msg="Log system verification start",
            meta={"test_name": "unified_logging"},
            env="test"
        )
        assert log.platform == Platform.BE
        assert log.level == LogLevel.INFO
        print(f"  [BE-LOG-01] Schema validation passed")

    def test_log_serializes_to_correct_json_keys(self):
        log = UnifiedLog(
            level=LogLevel.ERROR,
            trace_id="test-trace-001",
            platform=Platform.FE,
            category=EventCategory.ERROR,
            module="ChatPanel",
            action="send",
            msg="timeout",
            env="prod"
        )
        data = json.loads(log.model_dump_json())
        required_keys = {"ts", "level", "trace_id", "platform", "category", "module", "action", "msg", "meta", "env"}
        missing = required_keys - set(data.keys())
        assert not missing, f"Missing keys: {missing}"
        print(f"  [BE-LOG-01] JSON keys alignment passed")

# =============================================================================
# [LOG-02] Trace ID Context Propagation
# =============================================================================

class TestTraceIdPropagation:
    def test_trace_id_var_default(self):
        current = trace_id_var.get("system-internal")
        assert current == "system-internal"
        print(f"  [BE-LOG-02] Default trace_id check passed")

    def test_trace_id_isolation_between_contexts(self):
        results = {}

        async def simulate_request(name: str, tid: str):
            token = trace_id_var.set(tid)
            await asyncio.sleep(0.01)
            results[name] = trace_id_var.get()
            trace_id_var.reset(token)

        async def run():
            tid_a, tid_b = str(uuid.uuid4()), str(uuid.uuid4())
            await asyncio.gather(
                simulate_request("req_a", tid_a),
                simulate_request("req_b", tid_b),
            )
            assert results["req_a"] == tid_a
            assert results["req_b"] == tid_b
            print(f"  [BE-LOG-02] Concurrency isolation passed")

        asyncio.run(run())

# =============================================================================
# [LOG-03] Logger Binding and Field Injection
# =============================================================================

class TestGetTraceLogger:
    def test_trace_logger_injection(self):
        tid = "span-abc-123"
        token = trace_id_var.set(tid)
        captured_records = []
        
        # Add a temporary subscriber to capture output
        handler_id = loguru.logger.add(
            lambda msg: captured_records.append(json.loads(str(msg))),
            level="DEBUG",
            serialize=True,
        )
        try:
            tlog = get_trace_logger("TestModule")
            tlog.info("trigger log")
            assert len(captured_records) > 0
            rec = captured_records[-1]["record"]
            extra = rec["extra"]
            
            assert extra["trace_id"] == tid
            assert extra["module"] == "TestModule"
            assert extra["platform"] == "BE"
            print(f"  [BE-LOG-03] TraceLogger field injection passed")
        finally:
            loguru.logger.remove(handler_id)
            trace_id_var.reset(token)

# =============================================================================
# [LOG-04] File Output and SerDe
# =============================================================================

class TestJSONSerializationOutput:
    def test_serialized_log_structure(self, tmp_path):
        log_file = tmp_path / "test.log"
        handler_id = loguru.logger.add(str(log_file), serialize=True, level="DEBUG")

        try:
            loguru.logger.bind(trace_id="file-test").info("file content verification")
            loguru.logger.remove(handler_id)
            handler_id = None

            content = log_file.read_text(encoding="utf-8").strip()
            parsed = json.loads(content)
            assert "record" in parsed
            assert "text" in parsed
            print(f"  [BE-LOG-04] JSON File serialization passed")
        finally:
            if handler_id is not None:
                loguru.logger.remove(handler_id)

# =============================================================================
# [LOG-05] Middleware Integration
# =============================================================================

class TestTraceMiddleware:
    @pytest.mark.asyncio
    async def test_middleware_header_propagation(self):
        from httpx import AsyncClient, ASGITransport
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse
        from starlette.middleware.base import BaseHTTPMiddleware
        
        test_app = FastAPI()

        class MockTraceMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
                token = trace_id_var.set(trace_id)
                try:
                    response = await call_next(request)
                    response.headers["X-Trace-Id"] = trace_id
                    return response
                finally:
                    trace_id_var.reset(token)

        test_app.add_middleware(MockTraceMiddleware)

        @test_app.get("/ping")
        async def ping():
            return JSONResponse({"trace_id": trace_id_var.get()})

        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
            custom_tid = "custom-trace-id-12345"
            r = await client.get("/ping", headers={"X-Trace-Id": custom_tid})
            assert r.headers["X-Trace-Id"] == custom_tid
            assert r.json()["trace_id"] == custom_tid
            print(f"  [BE-LOG-05] Middleware integration passed")
