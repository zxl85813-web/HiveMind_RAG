"""add_folder_path_to_documents

Fix: 给 documents 表添加 folder_path 字段，支持文件夹层级结构。
同时修复 file_path 字段缺失问题（indexing.py 引用了 doc.file_path，
但模型只有 storage_path，此处添加 file_path 作为 storage_path 的别名列）。

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-27 14:00:00.000000
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # folder_path: 保留原始目录结构，例如 "技术文档/2024/API设计"
    # 对于单文件上传，此字段为 NULL
    op.add_column(
        "documents",
        sa.Column(
            "folder_path",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
            comment="原始文件夹路径，用于在 UI 中还原目录树结构",
        ),
    )
    op.create_index(
        "ix_documents_folder_path",
        "documents",
        ["folder_path"],
        unique=False,
    )

    # file_path: indexing.py 中使用 doc.file_path，与 storage_path 同义
    # 新上传的文件两个字段保持一致；历史数据通过 data migration 补填
    op.add_column(
        "documents",
        sa.Column(
            "file_path",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
            comment="文件路径（S3 key 或本地路径），与 storage_path 同义，供索引管道使用",
        ),
    )

    # 将现有 storage_path 数据回填到 file_path
    op.execute("UPDATE documents SET file_path = storage_path WHERE file_path IS NULL")


def downgrade() -> None:
    op.drop_index("ix_documents_folder_path", table_name="documents")
    op.drop_column("documents", "folder_path")
    op.drop_column("documents", "file_path")
