import pytest
from datetime import datetime
from app.models.governance import PromptDefinition, PromptStatus

def test_create_prompt_definition():
    """验证 PromptDefinition 的实例化与默认值"""
    prompt = PromptDefinition(
        slug="test_prompt",
        version="1.0.0",
        content="Hello {name}",
        recommended_model="gpt-4o"
    )
    
    assert prompt.slug == "test_prompt"
    assert prompt.version == "1.0.0"
    assert prompt.is_current is False
    assert prompt.status == PromptStatus.DRAFT
    assert isinstance(prompt.created_at, datetime)
    assert "name" in prompt.content

def test_prompt_definition_meta_info():
    """验证元数据 JSON 字段的存储"""
    meta = {"author": "antigravity", "estimated_tokens": 50}
    prompt = PromptDefinition(
        slug="metadata_test",
        version="0.1.0",
        content="...",
        meta_info=meta
    )
    
    assert prompt.meta_info["author"] == "antigravity"
    assert prompt.meta_info["estimated_tokens"] == 50

def test_prompt_status_enum():
    """验证枚举状态"""
    prompt = PromptDefinition(
        slug="status_test",
        version="1.1.0",
        content="...",
        status=PromptStatus.ACTIVE
    )
    assert prompt.status == "active"
    assert prompt.status == PromptStatus.ACTIVE
