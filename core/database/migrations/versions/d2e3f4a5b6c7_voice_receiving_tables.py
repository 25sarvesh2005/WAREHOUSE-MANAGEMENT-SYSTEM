"""voice_receiving_tables

Revision ID: d2e3f4a5b6c7
Revises: c1f2e3d4a5b6
Create Date: 2026-08-14 13:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, None] = "c1f2e3d4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _secure_table_for_supabase(table_name: str) -> None:
    """Enable RLS and withhold Supabase Data API role grants for a voice table."""
    op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                REVOKE ALL PRIVILEGES ON TABLE {table_name} FROM anon;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                REVOKE ALL PRIVILEGES ON TABLE {table_name} FROM authenticated;
            END IF;
        END
        $$;
        """
    )


def upgrade() -> None:
    """Create voice_interactions and voice_receiving_drafts tables with RLS."""
    op.create_table(
        "voice_interactions",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("actor_user_id", sa.UUID(), nullable=False),
        sa.Column("warehouse_id", sa.UUID(), nullable=True),
        sa.Column("receipt_id", sa.UUID(), nullable=True),
        sa.Column("provider_name", sa.String(length=50), nullable=False),
        sa.Column("stt_provider", sa.String(length=50), nullable=False),
        sa.Column("tts_provider", sa.String(length=50), nullable=True),
        sa.Column(
            "language_code",
            sa.String(length=20),
            server_default="en-IN",
            nullable=False,
        ),
        sa.Column("transcript_text", sa.Text(), nullable=True),
        sa.Column(
            "transcript_confidence", sa.Numeric(precision=5, scale=4), nullable=True
        ),
        sa.Column("parsed_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("safety_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("error_code", sa.String(length=50), nullable=True),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column("correlation_id", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_voice_interactions_actor_user_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["warehouse_id"],
            ["warehouses.id"],
            name=op.f("fk_voice_interactions_warehouse_id_warehouses"),
        ),
        sa.ForeignKeyConstraint(
            ["receipt_id"],
            ["receipts.id"],
            name=op.f("fk_voice_interactions_receipt_id_receipts"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_voice_interactions")),
    )
    op.create_index(
        "ix_voice_interactions_actor_created",
        "voice_interactions",
        ["actor_user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_voice_interactions_status_created",
        "voice_interactions",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_voice_interactions_actor_user_id"),
        "voice_interactions",
        ["actor_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_voice_interactions_status"),
        "voice_interactions",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_voice_interactions_correlation_id"),
        "voice_interactions",
        ["correlation_id"],
        unique=False,
    )

    _secure_table_for_supabase("voice_interactions")

    op.create_table(
        "voice_receiving_drafts",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("voice_interaction_id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=False),
        sa.Column("warehouse_id", sa.UUID(), nullable=True),
        sa.Column("product_id", sa.UUID(), nullable=True),
        sa.Column("receipt_id", sa.UUID(), nullable=True),
        sa.Column(
            "structured_lines",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=50),
            server_default="DRAFTED",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["voice_interaction_id"],
            ["voice_interactions.id"],
            name=op.f("fk_voice_receiving_drafts_voice_interaction_id_voice_interactions"),
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_voice_receiving_drafts_actor_user_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["warehouse_id"],
            ["warehouses.id"],
            name=op.f("fk_voice_receiving_drafts_warehouse_id_warehouses"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_voice_receiving_drafts_product_id_products"),
        ),
        sa.ForeignKeyConstraint(
            ["receipt_id"],
            ["receipts.id"],
            name=op.f("fk_voice_receiving_drafts_receipt_id_receipts"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_voice_receiving_drafts")),
    )
    op.create_index(
        "ix_voice_receiving_drafts_actor_created",
        "voice_receiving_drafts",
        ["actor_user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_voice_receiving_drafts_status_created",
        "voice_receiving_drafts",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_voice_receiving_drafts_actor_user_id"),
        "voice_receiving_drafts",
        ["actor_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_voice_receiving_drafts_voice_interaction_id"),
        "voice_receiving_drafts",
        ["voice_interaction_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_voice_receiving_drafts_status"),
        "voice_receiving_drafts",
        ["status"],
        unique=False,
    )

    _secure_table_for_supabase("voice_receiving_drafts")


def downgrade() -> None:
    """Drop voice_receiving_drafts and voice_interactions tables."""
    op.drop_index(op.f("ix_voice_receiving_drafts_status"), table_name="voice_receiving_drafts")
    op.drop_index(
        op.f("ix_voice_receiving_drafts_voice_interaction_id"),
        table_name="voice_receiving_drafts",
    )
    op.drop_index(
        op.f("ix_voice_receiving_drafts_actor_user_id"),
        table_name="voice_receiving_drafts",
    )
    op.drop_index(
        "ix_voice_receiving_drafts_status_created",
        table_name="voice_receiving_drafts",
    )
    op.drop_index(
        "ix_voice_receiving_drafts_actor_created",
        table_name="voice_receiving_drafts",
    )
    op.drop_table("voice_receiving_drafts")

    op.drop_index(op.f("ix_voice_interactions_correlation_id"), table_name="voice_interactions")
    op.drop_index(op.f("ix_voice_interactions_status"), table_name="voice_interactions")
    op.drop_index(op.f("ix_voice_interactions_actor_user_id"), table_name="voice_interactions")
    op.drop_index("ix_voice_interactions_status_created", table_name="voice_interactions")
    op.drop_index("ix_voice_interactions_actor_created", table_name="voice_interactions")
    op.drop_table("voice_interactions")
