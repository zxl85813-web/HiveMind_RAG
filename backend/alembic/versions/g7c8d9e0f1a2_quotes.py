"""quotes table + demo seed data.

Revision ID: g7c8d9e0f1a2
Revises: f6a7b8c9d0e1
Create Date: 2026-05-02
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import sqlalchemy as sa
from alembic import op


revision = "g7c8d9e0f1a2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    return name in sa.inspect(bind).get_table_names()


def upgrade() -> None:
    if not _has_table("quotes"):
        op.create_table(
            "quotes",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="default"),
            sa.Column("customer_name", sa.String(length=128), nullable=False),
            sa.Column("customer_phone", sa.String(length=32), nullable=False),
            sa.Column("customer_email", sa.String(length=128), nullable=False),
            sa.Column("customer_company", sa.String(length=128), nullable=True),
            sa.Column("product_name", sa.String(length=128), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("unit_price_cents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("amount_cents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
            sa.Column("region", sa.String(length=64), nullable=True),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_quotes_tenant_id", "quotes", ["tenant_id"])
        op.create_index("ix_quotes_created_at", "quotes", ["created_at"])

    # ---- Seed demo data (idempotent: only inserts if table empty) ----
    bind = op.get_bind()
    count = bind.execute(sa.text("SELECT COUNT(*) FROM quotes")).scalar() or 0
    if count == 0:
        rows = _build_seed_rows()
        bind.execute(
            sa.text(
                "INSERT INTO quotes (id, tenant_id, customer_name, customer_phone, "
                "customer_email, customer_company, product_name, quantity, "
                "unit_price_cents, amount_cents, currency, region, status, created_at) "
                "VALUES (:id, :tenant_id, :customer_name, :customer_phone, "
                ":customer_email, :customer_company, :product_name, :quantity, "
                ":unit_price_cents, :amount_cents, :currency, :region, :status, :created_at)"
            ),
            rows,
        )


def downgrade() -> None:
    if _has_table("quotes"):
        op.drop_index("ix_quotes_created_at", table_name="quotes")
        op.drop_index("ix_quotes_tenant_id", table_name="quotes")
        op.drop_table("quotes")


# ---------------------------------------------------------------------------

_CUSTOMERS = [
    ("Alice Chen", "13800001001", "alice.chen@acme.io", "Acme Robotics", "APAC"),
    ("Bob Wang", "13800001002", "bob.wang@globex.com", "Globex Corp", "APAC"),
    ("Carol Liu", "13800001003", "carol.liu@initech.cn", "Initech CN", "APAC"),
    ("David Zhao", "+1-415-555-0142", "d.zhao@umbrella.us", "Umbrella Health", "AMER"),
    ("Eva Martin", "+33-1-55-44-3322", "eva@hooli.fr", "Hooli FR", "EMEA"),
    ("Frank Müller", "+49-30-1234567", "frank@piedpiper.de", "Pied Piper DE", "EMEA"),
    ("Grace Park", "+82-2-555-1234", "g.park@stark.kr", "Stark KR", "APAC"),
    ("Henry Sun", "13800001008", "henry.sun@oscorp.cn", "Oscorp", "APAC"),
    ("Ivy Tanaka", "+81-3-9988-7766", "ivy@wayne.jp", "Wayne JP", "APAC"),
    ("Jack Brown", "+1-212-555-7788", "jack@lexcorp.us", "LexCorp", "AMER"),
]

_PRODUCTS = [
    ("HiveMind RAG Pro Annual", 9_900_00, 1),
    ("HiveMind RAG Enterprise", 49_900_00, 1),
    ("Agent Swarm Add-on Pack", 4_900_00, 3),
    ("Custom Skill Development", 12_000_00, 1),
    ("Premium Support (1y)", 6_000_00, 1),
    ("MCP Connector Bundle", 2_400_00, 5),
]

_STATUSES = ["draft", "sent", "won", "lost"]


def _build_seed_rows() -> list[dict]:
    rows = []
    base = datetime.utcnow() - timedelta(days=60)
    i = 0
    for cust in _CUSTOMERS:
        for prod in _PRODUCTS:
            i += 1
            name, phone, email, company, region = cust
            pname, unit_price, qty = prod
            amount = unit_price * qty
            rows.append(
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": "default",
                    "customer_name": name,
                    "customer_phone": phone,
                    "customer_email": email,
                    "customer_company": company,
                    "product_name": pname,
                    "quantity": qty,
                    "unit_price_cents": unit_price,
                    "amount_cents": amount,
                    "currency": "USD",
                    "region": region,
                    "status": _STATUSES[i % len(_STATUSES)],
                    "created_at": base + timedelta(days=i % 60, hours=i % 24),
                }
            )
    return rows
