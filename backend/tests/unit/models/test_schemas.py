"""
Pydantic Schema 验证测试。

覆盖:
    - ChatRequest 必填/选填字段
    - KnowledgeBaseCreate 默认值
    - TagCreate 验证
    - AIAction 类型
"""
import pytest
from pydantic import ValidationError

from app.schemas.chat import ChatRequest, ChatMessage, AIAction, ConversationListItem
from app.schemas.knowledge import KnowledgeBaseCreate, KnowledgeBaseUpdate, DocumentCreate
from app.schemas.tags import TagCreate, TagCategoryCreate


# ---------------------------------------------------------------------------
# Chat Schemas
# ---------------------------------------------------------------------------

class TestChatRequest:

    def test_minimal_request(self):
        req = ChatRequest(message="hello")
        assert req.message == "hello"
        assert req.conversation_id is None
        assert req.knowledge_base_ids == []
        assert req.stream is True

    def test_full_request(self):
        req = ChatRequest(
            message="test",
            conversation_id="conv_1",
            knowledge_base_ids=["kb_1", "kb_2"],
            model="gpt-4",
            stream=False,
        )
        assert req.model == "gpt-4"
        assert len(req.knowledge_base_ids) == 2

    def test_empty_message_is_valid(self):
        """Pydantic 不会拒绝空字符串，业务层负责校验。"""
        req = ChatRequest(message="")
        assert req.message == ""

    def test_missing_message_raises(self):
        with pytest.raises(ValidationError):
            ChatRequest()


class TestAIAction:

    def test_minimal_action(self):
        action = AIAction(type="navigate", label="Go", target="/dashboard")
        assert action.variant == "default"
        assert action.icon is None

    def test_full_action(self):
        action = AIAction(
            type="open_modal",
            label="Create KB",
            target="CreateKBModal",
            icon="plus",
            params={"preset": "legal"},
            variant="primary",
        )
        assert action.params["preset"] == "legal"


# ---------------------------------------------------------------------------
# Knowledge Schemas
# ---------------------------------------------------------------------------

class TestKnowledgeBaseCreate:

    def test_defaults(self):
        kb = KnowledgeBaseCreate(name="Test KB")
        assert kb.description == ""
        assert kb.is_public is False
        assert kb.chunking_strategy == "recursive"

    def test_custom_values(self):
        kb = KnowledgeBaseCreate(
            name="Legal KB",
            description="法律文档库",
            is_public=True,
            chunking_strategy="parent_child",
        )
        assert kb.is_public is True

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError):
            KnowledgeBaseCreate()


class TestKnowledgeBaseUpdate:

    def test_partial_update(self):
        update = KnowledgeBaseUpdate(name="New Name")
        assert update.name == "New Name"
        assert update.description is None
        assert update.is_public is None

    def test_empty_update_is_valid(self):
        update = KnowledgeBaseUpdate()
        assert update.name is None


class TestDocumentCreate:

    def test_valid_document(self):
        doc = DocumentCreate(
            filename="report.pdf",
            file_type="application/pdf",
            file_size=1024,
            storage_path="/uploads/report.pdf",
        )
        assert doc.content_hash is None


# ---------------------------------------------------------------------------
# Tag Schemas
# ---------------------------------------------------------------------------

class TestTagSchemas:

    def test_tag_create_defaults(self):
        tag = TagCreate(name="PDF")
        assert tag.color == "#64748b"
        assert tag.category_id is None

    def test_tag_create_with_category(self):
        tag = TagCreate(name="Legal", category_id=1, color="#ff0000")
        assert tag.category_id == 1

    def test_category_create(self):
        cat = TagCategoryCreate(name="文档类型")
        assert cat.description is None
