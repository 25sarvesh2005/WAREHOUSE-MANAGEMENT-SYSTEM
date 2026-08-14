"""ai_feedback_table

Revision ID: c1f2e3d4a5b6
Revises: b7e6d5c4a3f2
Create Date: 2026-08-14 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c1f2e3d4a5b6"
down_revision: Union[str, None] = "b7e6d5c4a3f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _secure_table_for_supabase(table_name: str) -> None:
    """Enable RLS and withhold Supabase Data API role grants for an AI table."""
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
    """Create audited ai_feedbacks table with Supabase RLS defense-in-depth."""
    op.create_table(
        "ai_feedbacks",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("ai_interaction_id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=False),
        sa.Column("is_helpful", sa.Boolean(), nullable=False),
        sa.Column("comment", sa.String(length=1000), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
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
            ["ai_interaction_id"],
            ["ai_interactions.id"],
            name=op.f("fk_ai_feedbacks_ai_interaction_id_ai_interactions"),
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_ai_feedbacks_actor_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_feedbacks")),
    )
    op.create_index(
        "ix_ai_feedbacks_interaction_actor",
        "ai_feedbacks",
        ["ai_interaction_id", "actor_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_feedbacks_actor_user_id"),
        "ai_feedbacks",
        ["actor_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_feedbacks_ai_interaction_id"),
        "ai_feedbacks",
        ["ai_interaction_id"],
        unique=False,
    )

    _secure_table_for_supabase("ai_feedbacks")


def downgrade() -> None:
    """Drop ai_feedbacks table."""
    op.drop_index(op.f("ix_ai_feedbacks_ai_interaction_id"), table_name="ai_feedbacks")
    op.drop_index(op.f("ix_ai_feedbacks_actor_user_id"), table_name="ai_feedbacks")
    op.drop_index("ix_ai_feedbacks_interaction_actor", table_name="ai_feedbacks")
    op.drop_table("ai_feedbacks")
