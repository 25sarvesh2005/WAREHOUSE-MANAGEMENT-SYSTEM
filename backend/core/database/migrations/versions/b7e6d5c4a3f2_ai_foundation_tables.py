"""ai_foundation_tables

Revision ID: b7e6d5c4a3f2
Revises: a6c2d8e4f0b1
Create Date: 2026-08-14 10:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b7e6d5c4a3f2"
down_revision: Union[str, None] = "a6c2d8e4f0b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

AI_TABLES: tuple[str, ...] = (
    "ai_interactions",
    "ai_tool_calls",
    "ai_draft_actions",
)


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
    """Create audited AI foundation tables with Supabase RLS defense-in-depth."""
    op.create_table(
        "ai_interactions",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("actor_user_id", sa.UUID(), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("request_category", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("provider_name", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("prompt_hash", sa.String(length=64), nullable=False),
        sa.Column("prompt_excerpt", sa.String(length=500), nullable=True),
        sa.Column("response_excerpt", sa.String(length=2000), nullable=True),
        sa.Column("safety_decision", sa.String(length=100), nullable=False),
        sa.Column("refusal_reason", sa.String(length=1000), nullable=True),
        sa.Column(
            "seller_scope",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "warehouse_scope",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "retrieved_references",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
            name=op.f("fk_ai_interactions_actor_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_interactions")),
        sa.UniqueConstraint("correlation_id", name="uq_ai_interactions_correlation_id"),
    )
    op.create_index(
        "ix_ai_interactions_actor_status",
        "ai_interactions",
        ["actor_user_id", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_interactions_actor_user_id"),
        "ai_interactions",
        ["actor_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_interactions_correlation_id"),
        "ai_interactions",
        ["correlation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_interactions_request_category"),
        "ai_interactions",
        ["request_category"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_interactions_safety_decision"),
        "ai_interactions",
        ["safety_decision"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_interactions_status"),
        "ai_interactions",
        ["status"],
        unique=False,
    )

    op.create_table(
        "ai_tool_calls",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("ai_interaction_id", sa.UUID(), nullable=False),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column(
            "permission_scope",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("input_excerpt", sa.String(length=1000), nullable=True),
        sa.Column("output_reference_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
            name=op.f("fk_ai_tool_calls_ai_interaction_id_ai_interactions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_tool_calls")),
    )
    op.create_index(
        "ix_ai_tool_calls_interaction_status",
        "ai_tool_calls",
        ["ai_interaction_id", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_tool_calls_ai_interaction_id"),
        "ai_tool_calls",
        ["ai_interaction_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_tool_calls_status"),
        "ai_tool_calls",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_tool_calls_tool_name"),
        "ai_tool_calls",
        ["tool_name"],
        unique=False,
    )

    op.create_table(
        "ai_draft_actions",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("ai_interaction_id", sa.UUID(), nullable=False),
        sa.Column("action_type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("target_record_type", sa.String(length=100), nullable=True),
        sa.Column("target_record_id", sa.UUID(), nullable=True),
        sa.Column("draft_payload_hash", sa.String(length=64), nullable=False),
        sa.Column("draft_payload_excerpt", sa.String(length=2000), nullable=True),
        sa.Column("requires_approval", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("approved_by_user_id", sa.UUID(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.String(length=1000), nullable=True),
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
            name=op.f("fk_ai_draft_actions_ai_interaction_id_ai_interactions"),
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_user_id"],
            ["users.id"],
            name=op.f("fk_ai_draft_actions_approved_by_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_draft_actions")),
    )
    op.create_index(
        "ix_ai_draft_actions_interaction_status",
        "ai_draft_actions",
        ["ai_interaction_id", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_draft_actions_action_type"),
        "ai_draft_actions",
        ["action_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_draft_actions_ai_interaction_id"),
        "ai_draft_actions",
        ["ai_interaction_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_draft_actions_approved_by_user_id"),
        "ai_draft_actions",
        ["approved_by_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_draft_actions_status"),
        "ai_draft_actions",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_draft_actions_target_record_id"),
        "ai_draft_actions",
        ["target_record_id"],
        unique=False,
    )

    for table_name in AI_TABLES:
        _secure_table_for_supabase(table_name)


def downgrade() -> None:
    """Drop audited AI foundation tables."""
    op.drop_index(op.f("ix_ai_draft_actions_target_record_id"), table_name="ai_draft_actions")
    op.drop_index(op.f("ix_ai_draft_actions_status"), table_name="ai_draft_actions")
    op.drop_index(
        op.f("ix_ai_draft_actions_approved_by_user_id"),
        table_name="ai_draft_actions",
    )
    op.drop_index(
        op.f("ix_ai_draft_actions_ai_interaction_id"),
        table_name="ai_draft_actions",
    )
    op.drop_index(op.f("ix_ai_draft_actions_action_type"), table_name="ai_draft_actions")
    op.drop_index("ix_ai_draft_actions_interaction_status", table_name="ai_draft_actions")
    op.drop_table("ai_draft_actions")

    op.drop_index(op.f("ix_ai_tool_calls_tool_name"), table_name="ai_tool_calls")
    op.drop_index(op.f("ix_ai_tool_calls_status"), table_name="ai_tool_calls")
    op.drop_index(op.f("ix_ai_tool_calls_ai_interaction_id"), table_name="ai_tool_calls")
    op.drop_index("ix_ai_tool_calls_interaction_status", table_name="ai_tool_calls")
    op.drop_table("ai_tool_calls")

    op.drop_index(op.f("ix_ai_interactions_status"), table_name="ai_interactions")
    op.drop_index(op.f("ix_ai_interactions_safety_decision"), table_name="ai_interactions")
    op.drop_index(op.f("ix_ai_interactions_request_category"), table_name="ai_interactions")
    op.drop_index(op.f("ix_ai_interactions_correlation_id"), table_name="ai_interactions")
    op.drop_index(op.f("ix_ai_interactions_actor_user_id"), table_name="ai_interactions")
    op.drop_index("ix_ai_interactions_actor_status", table_name="ai_interactions")
    op.drop_table("ai_interactions")
