from app.prompts.engine import PromptEngine


def test_agent_prompt_head_tail_variant_contains_tail_anchor_lines():
    engine = PromptEngine()

    prompt = engine.build_agent_prompt(
        agent_name="rag_agent",
        task="answer a retrieval task",
        rag_context="[1] sample context",
        prompt_variant="head_tail_v1",
    )

    assert "## Final Guardrails (Tail Anchor)" in prompt
    assert "Re-check the task goal before answering" in prompt


def test_agent_prompt_default_variant_uses_short_tail_anchor():
    engine = PromptEngine()

    prompt = engine.build_agent_prompt(
        agent_name="rag_agent",
        task="answer a retrieval task",
        rag_context="[1] sample context",
    )

    assert "## Final Guardrails (Tail Anchor)" in prompt
    assert "Follow system safety and role constraints strictly." in prompt
