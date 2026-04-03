import asyncio
import pytest
from app.services.sandbox.safe_environment import SafeEnvironment

@pytest.mark.asyncio
async def test_sandbox_blocked_import():
    """Verify that importing unauthorized modules is blocked."""
    env = SafeEnvironment()
    code = "import os\nprint(os.getcwd())"
    result = await env.execute(code)
    assert "Error" in result
    assert "import" in result.lower()

@pytest.mark.asyncio
async def test_sandbox_blocked_getattr():
    """Verify that accessing private attributes (dunder) is blocked."""
    env = SafeEnvironment()
    # Attempting to get subclasses of object to find a way to os
    code = "classes = ().__class__.__base__.__subclasses__()\nreturn str(classes)"
    result = await env.execute(code)
    assert "Error" in result
    assert "private attribute" in result.lower()

@pytest.mark.asyncio
async def test_sandbox_timeout():
    """Verify that infinite loops are caught by the timeout."""
    env = SafeEnvironment()
    code = "while True:\n    pass"
    # Execution should time out
    result = await env.execute(code, timeout=0.1)
    assert "timeout" in result.lower()

@pytest.mark.asyncio
async def test_sandbox_valid_code():
    """Verify that safe code runs successfully."""
    env = SafeEnvironment()
    code = "x = 10\ny = 20\nreturn x + y"
    result = await env.execute(code)
    assert result == 30

@pytest.mark.asyncio
async def test_sandbox_tool_call_simulation():
    """Verify that the platform bridge works with async calls."""
    class MockBridge:
        async def call(self, name, **kwargs):
            return f"Called {name} with {kwargs}"

    bridge = MockBridge()
    env = SafeEnvironment(platform_bridge=bridge)
    code = "res = await platform.call('search', query='test')\nreturn res"
    result = await env.execute(code)
    assert result == "Called search with {'query': 'test'}"
