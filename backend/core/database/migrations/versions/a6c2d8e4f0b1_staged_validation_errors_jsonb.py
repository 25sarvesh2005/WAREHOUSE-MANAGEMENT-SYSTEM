"""staged_validation_errors_jsonb

Revision ID: a6c2d8e4f0b1
Revises: f5a1b2c3d4e5
Create Date: 2026-08-13 23:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a6c2d8e4f0b1"
down_revision: Union[str, None] = "f5a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert staged row validation errors to PostgreSQL JSONB."""
    op.alter_column(
        "staged_opening_inventory_rows",
        "validation_errors",
        existing_type=sa.JSON(),
        type_=postgresql.JSONB(),
        existing_nullable=False,
        postgresql_using="validation_errors::jsonb",
    )


def downgrade() -> None:
    """Convert staged row validation errors back to generic JSON."""
    op.alter_column(
        "staged_opening_inventory_rows",
        "validation_errors",
        existing_type=postgresql.JSONB(),
        type_=sa.JSON(),
        existing_nullable=False,
        postgresql_using="validation_errors::json",
    )
