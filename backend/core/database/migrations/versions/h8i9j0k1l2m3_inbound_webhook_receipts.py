"""Persist inbound webhook delivery IDs to prevent replay processing.

Revision ID: h8i9j0k1l2m3
Revises: d2e3f4a5b6c7, g1h2i3j4k5l6
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "h8i9j0k1l2m3"
down_revision: str | Sequence[str] | None = ("d2e3f4a5b6c7", "g1h2i3j4k5l6")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "inbound_webhook_receipts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("delivery_id", sa.String(length=255), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inbound_webhook_receipts")),
        sa.UniqueConstraint(
            "provider",
            "delivery_id",
            name="uq_inbound_webhook_receipts_provider_delivery_id",
        ),
    )
    op.execute("ALTER TABLE inbound_webhook_receipts ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                REVOKE ALL PRIVILEGES ON TABLE inbound_webhook_receipts FROM anon;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                REVOKE ALL PRIVILEGES ON TABLE inbound_webhook_receipts FROM authenticated;
            END IF;
        END
        $$;
        """
    )
    op.create_index(
        op.f("ix_inbound_webhook_receipts_received_at"),
        "inbound_webhook_receipts",
        ["received_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_inbound_webhook_receipts_received_at"),
        table_name="inbound_webhook_receipts",
    )
    op.drop_table("inbound_webhook_receipts")
