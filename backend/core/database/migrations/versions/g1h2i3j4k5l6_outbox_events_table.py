"""outbox_events_table

Revision ID: g1h2i3j4k5l6
Revises: a6c2d8e4f0b1
Create Date: 2026-08-18 20:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "g1h2i3j4k5l6"
down_revision: Union[str, None] = "a6c2d8e4f0b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create outbox_events table with performance indexes for background polling."""
    op.create_table(
        "outbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(op.f("ix_outbox_events_event_type"), "outbox_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_outbox_events_status"), "outbox_events", ["status"], unique=False)
    op.create_index(op.f("ix_outbox_events_next_attempt_at"), "outbox_events", ["next_attempt_at"], unique=False)
    op.create_index(
        "ix_outbox_events_status_next_attempt",
        "outbox_events",
        ["status", "next_attempt_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop outbox_events table and indexes."""
    op.drop_index("ix_outbox_events_status_next_attempt", table_name="outbox_events")
    op.drop_index(op.f("ix_outbox_events_next_attempt_at"), table_name="outbox_events")
    op.drop_index(op.f("ix_outbox_events_status"), table_name="outbox_events")
    op.drop_index(op.f("ix_outbox_events_event_type"), table_name="outbox_events")
    op.drop_table("outbox_events")
