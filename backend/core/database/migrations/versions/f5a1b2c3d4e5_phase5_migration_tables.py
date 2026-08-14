"""phase5_migration_tables

Revision ID: f5a1b2c3d4e5
Revises: e2b7a4c9d8f1
Create Date: 2026-08-13 23:05:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f5a1b2c3d4e5"
down_revision: Union[str, None] = "e2b7a4c9d8f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create import_batches and staged_opening_inventory_rows tables."""
    op.create_table(
        "import_batches",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("batch_number", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="STAGED"),
        sa.Column("source_notes", sa.String(length=500), nullable=True),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
        sa.Column("approved_by_user_id", sa.UUID(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invalid_rows", sa.Integer(), nullable=False, server_default="0"),
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
            ["approved_by_user_id"],
            ["users.id"],
            name=op.f("fk_import_batches_approved_by_user_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_import_batches_created_by_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_batches")),
        sa.UniqueConstraint("batch_number", name=op.f("uq_import_batches_batch_number")),
    )
    op.create_index(
        op.f("ix_import_batches_approved_by_user_id"),
        "import_batches",
        ["approved_by_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_import_batches_batch_number"),
        "import_batches",
        ["batch_number"],
        unique=True,
    )
    op.create_index(
        op.f("ix_import_batches_created_by_user_id"),
        "import_batches",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_import_batches_status"),
        "import_batches",
        ["status"],
        unique=False,
    )

    op.create_table(
        "staged_opening_inventory_rows",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("import_batch_id", sa.UUID(), nullable=False),
        sa.Column("source_workbook", sa.String(length=255), nullable=False),
        sa.Column("source_sheet", sa.String(length=255), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("raw_seller_code", sa.String(length=100), nullable=True),
        sa.Column("raw_sku", sa.String(length=100), nullable=True),
        sa.Column("raw_upc", sa.String(length=100), nullable=True),
        sa.Column("raw_warehouse_code", sa.String(length=100), nullable=True),
        sa.Column("raw_location_code", sa.String(length=100), nullable=True),
        sa.Column("raw_inventory_state", sa.String(length=50), nullable=True),
        sa.Column("raw_quantity", sa.String(length=100), nullable=True),
        sa.Column("seller_id", sa.UUID(), nullable=True),
        sa.Column("product_id", sa.UUID(), nullable=True),
        sa.Column("warehouse_id", sa.UUID(), nullable=True),
        sa.Column("location_id", sa.UUID(), nullable=True),
        sa.Column("inventory_state", sa.String(length=50), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column(
            "validation_status",
            sa.String(length=50),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("validation_errors", postgresql.JSONB(), nullable=False),
        sa.Column("applied_movement_id", sa.UUID(), nullable=True),
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
            ["applied_movement_id"],
            ["inventory_movements.id"],
            name=op.f("fk_staged_opening_inventory_rows_applied_movement_id_inventory_movements"),
        ),
        sa.ForeignKeyConstraint(
            ["import_batch_id"],
            ["import_batches.id"],
            name=op.f("fk_staged_opening_inventory_rows_import_batch_id_import_batches"),
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["warehouse_locations.id"],
            name=op.f("fk_staged_opening_inventory_rows_location_id_warehouse_locations"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_staged_opening_inventory_rows_product_id_products"),
        ),
        sa.ForeignKeyConstraint(
            ["seller_id"],
            ["sellers.id"],
            name=op.f("fk_staged_opening_inventory_rows_seller_id_sellers"),
        ),
        sa.ForeignKeyConstraint(
            ["warehouse_id"],
            ["warehouses.id"],
            name=op.f("fk_staged_opening_inventory_rows_warehouse_id_warehouses"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_staged_opening_inventory_rows")),
        sa.UniqueConstraint(
            "import_batch_id",
            "source_workbook",
            "source_sheet",
            "source_row_number",
            name="uq_staged_row_identity",
        ),
        sa.UniqueConstraint(
            "import_batch_id",
            "source_hash",
            name="uq_staged_row_hash",
        ),
    )
    op.create_index(
        op.f("ix_staged_opening_inventory_rows_applied_movement_id"),
        "staged_opening_inventory_rows",
        ["applied_movement_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_staged_opening_inventory_rows_import_batch_id"),
        "staged_opening_inventory_rows",
        ["import_batch_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_staged_opening_inventory_rows_inventory_state"),
        "staged_opening_inventory_rows",
        ["inventory_state"],
        unique=False,
    )
    op.create_index(
        op.f("ix_staged_opening_inventory_rows_location_id"),
        "staged_opening_inventory_rows",
        ["location_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_staged_opening_inventory_rows_product_id"),
        "staged_opening_inventory_rows",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_staged_opening_inventory_rows_seller_id"),
        "staged_opening_inventory_rows",
        ["seller_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_staged_opening_inventory_rows_validation_status"),
        "staged_opening_inventory_rows",
        ["validation_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_staged_opening_inventory_rows_warehouse_id"),
        "staged_opening_inventory_rows",
        ["warehouse_id"],
        unique=False,
    )
    op.create_index(
        "ix_staged_batch_status",
        "staged_opening_inventory_rows",
        ["import_batch_id", "validation_status"],
        unique=False,
    )


def downgrade() -> None:
    """Drop staged_opening_inventory_rows and import_batches tables."""
    op.drop_index("ix_staged_batch_status", table_name="staged_opening_inventory_rows")
    op.drop_index(
        op.f("ix_staged_opening_inventory_rows_warehouse_id"),
        table_name="staged_opening_inventory_rows",
    )
    op.drop_index(
        op.f("ix_staged_opening_inventory_rows_validation_status"),
        table_name="staged_opening_inventory_rows",
    )
    op.drop_index(
        op.f("ix_staged_opening_inventory_rows_seller_id"),
        table_name="staged_opening_inventory_rows",
    )
    op.drop_index(
        op.f("ix_staged_opening_inventory_rows_product_id"),
        table_name="staged_opening_inventory_rows",
    )
    op.drop_index(
        op.f("ix_staged_opening_inventory_rows_location_id"),
        table_name="staged_opening_inventory_rows",
    )
    op.drop_index(
        op.f("ix_staged_opening_inventory_rows_inventory_state"),
        table_name="staged_opening_inventory_rows",
    )
    op.drop_index(
        op.f("ix_staged_opening_inventory_rows_import_batch_id"),
        table_name="staged_opening_inventory_rows",
    )
    op.drop_index(
        op.f("ix_staged_opening_inventory_rows_applied_movement_id"),
        table_name="staged_opening_inventory_rows",
    )
    op.drop_table("staged_opening_inventory_rows")

    op.drop_index(op.f("ix_import_batches_status"), table_name="import_batches")
    op.drop_index(
        op.f("ix_import_batches_created_by_user_id"), table_name="import_batches"
    )
    op.drop_index(
        op.f("ix_import_batches_batch_number"), table_name="import_batches"
    )
    op.drop_index(
        op.f("ix_import_batches_approved_by_user_id"), table_name="import_batches"
    )
    op.drop_table("import_batches")
