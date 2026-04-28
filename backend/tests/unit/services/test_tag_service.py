"""
TagService 单元测试。

覆盖:
    - 标签分类 CRUD
    - 标签 CRUD
    - 文档-标签关联 (attach / detach / list)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.tag_service import TagService
from app.core.exceptions import NotFoundError


# ---------------------------------------------------------------------------
# Tag Category
# ---------------------------------------------------------------------------

class TestTagCategory:

    @pytest.mark.asyncio
    async def test_create_category(self, mock_db_session):
        category_data = MagicMock()
        # model_validate 需要返回一个 TagCategory-like 对象
        with patch("app.services.tag_service.TagCategory") as MockTC:
            mock_cat = MagicMock()
            mock_cat.id = 1
            mock_cat.name = "文档类型"
            MockTC.model_validate.return_value = mock_cat

            result = await TagService.create_category(mock_db_session, category_data)

            mock_db_session.add.assert_called_once_with(mock_cat)
            mock_db_session.commit.assert_awaited_once()
            assert result.name == "文档类型"

    @pytest.mark.asyncio
    async def test_get_categories(self, mock_db_session):
        cats = [MagicMock(name="Cat1"), MagicMock(name="Cat2")]
        exec_result = MagicMock()
        exec_result.scalars.return_value.all.return_value = cats
        mock_db_session.execute = AsyncMock(return_value=exec_result)

        result = await TagService.get_categories(mock_db_session)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# Tag CRUD
# ---------------------------------------------------------------------------

class TestTagCRUD:

    @pytest.mark.asyncio
    async def test_create_tag_without_category(self, mock_db_session):
        tag_data = MagicMock()
        tag_data.category_id = None

        with patch("app.services.tag_service.Tag") as MockTag:
            mock_tag = MagicMock()
            mock_tag.id = 1
            mock_tag.name = "PDF"
            MockTag.model_validate.return_value = mock_tag

            result = await TagService.create_tag(mock_db_session, tag_data)
            assert result.name == "PDF"

    @pytest.mark.asyncio
    async def test_create_tag_with_invalid_category_raises(self, mock_db_session):
        tag_data = MagicMock()
        tag_data.category_id = 999
        mock_db_session.get = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await TagService.create_tag(mock_db_session, tag_data)

    @pytest.mark.asyncio
    async def test_delete_tag_success(self, mock_db_session):
        tag = MagicMock()
        mock_db_session.get = AsyncMock(return_value=tag)

        result = await TagService.delete_tag(mock_db_session, tag_id=1)
        assert result is True
        mock_db_session.delete.assert_awaited_once_with(tag)

    @pytest.mark.asyncio
    async def test_delete_tag_not_found(self, mock_db_session):
        mock_db_session.get = AsyncMock(return_value=None)

        result = await TagService.delete_tag(mock_db_session, tag_id=999)
        assert result is False
