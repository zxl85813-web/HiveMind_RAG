"""
数据库种子脚本 — 为 Security 模块插入初始演示数据。

运行方式:
    cd backend
    python -m app.scripts.seed_security
"""

import asyncio
import json
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import select

from app.core.config import settings
from app.models.security import (
    AuditLog,
    DesensitizationPolicy,
)


async def seed():
    url = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}/{settings.POSTGRES_DB}"
    engine = create_async_engine(url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # === 检查是否已有数据 ===
        existing = (await db.execute(select(DesensitizationPolicy))).scalars().first()
        if existing:
            print("[Seed] Security data already exists, skipping.")
            await engine.dispose()
            return

        now = datetime.utcnow()

        # === 1. 脱敏策略 ===
        policies = [
            DesensitizationPolicy(
                name="默认企业脱敏策略",
                description="覆盖身份证、手机号、银行卡、邮箱等常见敏感信息",
                is_active=True,
                rules_json=json.dumps(
                    [
                        {"type": "id_card", "action": "mask", "enabled": True},
                        {"type": "phone", "action": "mask", "enabled": True},
                        {"type": "email", "action": "mask", "enabled": True},
                        {"type": "bank_card", "action": "mask", "enabled": True},
                    ],
                    ensure_ascii=False,
                ),
                created_at=now - timedelta(days=30),
                updated_at=now - timedelta(days=5),
            ),
            DesensitizationPolicy(
                name="最小化脱敏策略",
                description="仅检测身份证号，适用于内部文档",
                is_active=False,
                rules_json=json.dumps(
                    [
                        {"type": "id_card", "action": "mask", "enabled": True},
                    ],
                    ensure_ascii=False,
                ),
                created_at=now - timedelta(days=20),
                updated_at=now - timedelta(days=20),
            ),
            DesensitizationPolicy(
                name="严格审计策略",
                description="全类型检测 + 替换模式，适用于对外发布文档",
                is_active=False,
                rules_json=json.dumps(
                    [
                        {"type": "id_card", "action": "replace", "enabled": True},
                        {"type": "phone", "action": "replace", "enabled": True},
                        {"type": "email", "action": "replace", "enabled": True},
                        {"type": "bank_card", "action": "replace", "enabled": True},
                        {"type": "address", "action": "replace", "enabled": True},
                        {"type": "name", "action": "replace", "enabled": True},
                    ],
                    ensure_ascii=False,
                ),
                created_at=now - timedelta(days=10),
                updated_at=now - timedelta(days=10),
            ),
        ]

        for p in policies:
            db.add(p)

        # === 2. 审计日志 ===
        audit_logs = [
            AuditLog(
                user_id="user-001",
                action="activate_policy",
                resource_type="security_policy",
                resource_id="1",
                details=json.dumps({"name": "默认企业脱敏策略"}, ensure_ascii=False),
                ip_address="192.168.1.100",
                timestamp=now - timedelta(hours=2),
            ),
            AuditLog(
                user_id="user-001",
                action="create_policy",
                resource_type="security_policy",
                resource_id="3",
                details=json.dumps({"name": "严格审计策略"}, ensure_ascii=False),
                ip_address="192.168.1.100",
                timestamp=now - timedelta(hours=5),
            ),
            AuditLog(
                user_id="user-001",
                action="upload_document",
                resource_type="document",
                resource_id="doc-003",
                details=json.dumps({"filename": "API_Contract_Draft.md"}, ensure_ascii=False),
                ip_address="192.168.1.100",
                timestamp=now - timedelta(days=1),
            ),
            AuditLog(
                user_id="user-001",
                action="create_kb",
                resource_type="knowledge_base",
                resource_id="kb-001",
                details=json.dumps({"name": "企业制度知识库"}, ensure_ascii=False),
                ip_address="192.168.1.100",
                timestamp=now - timedelta(days=2),
            ),
            AuditLog(
                user_id="user-001",
                action="login",
                resource_type="session",
                resource_id="sess-101",
                details=json.dumps({"ip": "192.168.1.100"}, ensure_ascii=False),
                ip_address="192.168.1.100",
                timestamp=now - timedelta(days=3),
            ),
        ]

        for log in audit_logs:
            db.add(log)

        await db.commit()
        print("[Seed] Security data seeded successfully!")
        print(f"  - {len(policies)} desensitization policies")
        print(f"  - {len(audit_logs)} audit logs")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
