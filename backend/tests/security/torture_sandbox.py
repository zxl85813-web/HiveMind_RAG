"""
Torture Test for HiveMind Sandbox (SafeEnvironment).
Tries to escape, cause OOM, or RCE.
Used in M3 Regression Phase.
"""

import asyncio
import pytest
from app.services.sandbox.safe_environment import SafeEnvironment

@pytest.mark.asyncio
async def test_rce_escape_attempts():
    env = SafeEnvironment()
    
    # 💥 Attempt 1: Classic __subclasses__ escape
    code_1 = """
def escape():
    return [].__class__.__base__.__subclasses__()
result = escape()
    """
    res_1 = await env.execute(code_1)
    assert "Denied access to private attribute" in str(res_1) or "Error" in str(res_1)

    # 💥 Attempt 2: Import os
    code_2 = """
import os
os.system('echo hacked')
    """
    res_2 = await env.execute(code_2)
    assert "Import" in str(res_2) or "denied" in str(res_2).lower() or "Error" in str(res_2)

    # 💥 Attempt 3: Builtins access
    code_3 = """
__builtins__['eval']('print("leak")')
    """
    res_3 = await env.execute(code_3)
    assert "Error" in str(res_3)

@pytest.mark.asyncio
async def test_resource_exhaustion():
    env = SafeEnvironment()
    
    # 💥 Attempt 4: Infinite loop (Timeout check)
    code_4 = """
while True:
    pass
    """
    res_4 = await env.execute(code_4, timeout=1.0)
    assert "exceeded the timeout" in str(res_4)

    # 💥 Attempt 5: Recursion depth
    code_5 = """
def recurse():
    return recurse()
recurse()
    """
    res_5 = await env.execute(code_5)
    assert "maximum recursion depth exceeded" in str(res_5).lower() or "Error" in str(res_5)

@pytest.mark.asyncio
async def test_async_capabilities():
    # If this fails, our Sandbox is not yet ready for P2 agents
    env = SafeEnvironment()
    code = """
async def main():
    return "Hello from Async"
result = await main()
    """
    res = await env.execute(code)
    # If the sandbox doesn't support async, this will fail
    assert res == "Hello from Async"
