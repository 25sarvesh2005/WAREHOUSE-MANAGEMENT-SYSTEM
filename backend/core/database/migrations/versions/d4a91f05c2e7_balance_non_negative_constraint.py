"""balance_non_negative_constraint

Revision ID: d4a91f05c2e7
Revises: 671b43c62846
Create Date: 2026-08-13 16:12:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4a91f05c2e7"
down_revision: str | None = "671b43c62846"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the non-negative balance guard required for inventory hardening."""
    op.create_check_constraint(
        "ck_balance_non_negative",
        "inventory_balances",
        "quantity >= 0",
    )


def downgrade() -> None:
    """Remove the non-negative balance guard."""
    op.drop_constraint(
        "ck_balance_non_negative",
        "inventory_balances",
        type_="check",
    )
