"""
HiveMind Harness SDK
====================
图谱感知的运行时治理引擎。

用法:
    from app.sdk.harness.engine import get_harness_engine

    engine = get_harness_engine()
    result = await engine.check_agent_output(
        content=agent_output,
        agent_name="CodeAgent",
        task_id="t1",
        output_type="code",
    )
    if not result.passed:
        # 处理 error 级别的失败
        ...
"""
