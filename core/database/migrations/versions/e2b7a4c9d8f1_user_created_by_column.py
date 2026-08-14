"""user_created_by_column

Revision ID: e2b7a4c9d8f1
Revises: d4a91f05c2e7
Create Date: 2026-08-13 16:35:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e2b7a4c9d8f1"
down_revision: Union[str, None] = "d4a91f05c2e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add self-referential staff creator tracking to users."""
    op.add_column("users", sa.Column("created_by_user_id", sa.UUID(), nullable=True))
    op.create_index(
        op.f("ix_users_created_by_user_id"),
        "users",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_foreign_key(
        op.f("fk_users_created_by_user_id_users"),
        "users",
        "users",
        ["created_by_user_id"],
        ["id"],
    )


def downgrade() -> None:
    """Remove self-referential staff creator tracking from users."""
    op.drop_constraint(
        op.f("fk_users_created_by_user_id_users"),
        "users",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_users_created_by_user_id"), table_name="users")
    op.drop_column("users", "created_by_user_id")
