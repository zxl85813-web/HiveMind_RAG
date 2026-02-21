"""
自动测试生成器 — 根据代码模板生成 pytest 骨架。

用法:
    python .agent/testing/generate_test.py <module_name> <class_name>

    示例:
    python .agent/testing/generate_test.py app.services.user_service UserService

    将会在: tests/unit/services/test_user_service.py 生成测试骨架。
"""

import sys
import os
from pathlib import Path

TEMPLATE = """
import pytest
from unittest.mock import AsyncMock, MagicMock

# 待测试模块
from {{ module_name }} import {{ class_name }}

@pytest.fixture
def mock_db_session():
    \"\"\"Mock 数据库会话\"\"\"
    session = AsyncMock()
    # 可以在此设置返回值
    return session

@pytest.mark.asyncio
async def test_{{ method_prefix }}_create(mock_db_session):
    \"\"\"测试创建逻辑\"\"\"
    # Arrange
    data = {"name": "test_object"}
    
    # Act
    # result = await {{ class_name }}.create(data)

    # Assert
    # assert result.name == "test_object"
    pass

@pytest.mark.asyncio
async def test_{{ method_prefix }}_get_not_found():
    \"\"\"测试异常流\"\"\"
    # Arrange
    
    # Act & Assert
    # with pytest.raises(NotFoundError):
    #     await {{ class_name }}.get("invalid-id")
    pass
"""

def generate_test(module_name: str, class_name: str):
    print(f"🛠️ Generating test for {class_name} in {module_name}...")
    
    # 解析路径
    parts = module_name.split(".")
    #假设 app.services.user_service -> tests/unit/services/test_user_service.py
    # app/ -> tests/unit/
    
    if parts[0] == "app":
        test_dir_parts = ["tests", "unit"] + parts[1:-1]
        file_name = f"test_{parts[-1]}.py"
    else:
        test_dir_parts = ["tests", "unit"]
        file_name = f"test_generated.py"

    base_dir = Path(__file__).resolve().parent.parent.parent #回到根目录
    test_dir = base_dir.joinpath(*test_dir_parts)
    test_file = test_dir / file_name

    # 创建目录
    test_dir.mkdir(parents=True, exist_ok=True)
    
    if test_file.exists():
        print(f"⚠️ Test file already exists: {test_file}")
        return

    # 生成内容
    content = TEMPLATE.replace("{{ module_name }}", module_name)\
                      .replace("{{ class_name }}", class_name)\
                      .replace("{{ method_prefix }}", class_name.lower())

    with open(test_file, "w", encoding="utf-8") as f:
        f.write(content)
        
    print(f"✅ Generated test skeleton: {test_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_test.py <module_name> <class_name>")
        sys.exit(1)
        
    generate_test(sys.argv[1], sys.argv[2])
