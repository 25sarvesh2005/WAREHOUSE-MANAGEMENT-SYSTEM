"""
--------------------------------------------------------------------------------
File        : tests/unit/test_opening_inventory_parser.py
Purpose     : Validate opening inventory CSV/XLSX parser behavior.

Responsibilities:
    - Verify raw value preservation and source metadata.
    - Verify required-column and unsupported-file validation.
    - Verify deterministic source hashes.

Flow:
    pytest -> opening_inventory_parser -> assertions

Used By:
    - Phase 5 file import validation.

Returns:
    test_*() -> None - Pytest assertion handlers.

Raises:
    AssertionError: If parser behavior diverges.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest

from core.services.import_export.opening_inventory_parser import (
    compute_opening_inventory_row_hash,
    parse_opening_inventory_csv,
    parse_opening_inventory_file,
    parse_opening_inventory_xlsx,
)

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def test_parse_opening_inventory_csv_preserves_raw_source_values() -> None:
    """Verify CSV parsing preserves raw values and source metadata."""
    file_bytes = (FIXTURES_DIR / "opening_inventory_valid.csv").read_bytes()

    rows = parse_opening_inventory_csv("opening_inventory_valid.csv", file_bytes)

    assert len(rows) == 2
    assert rows[0]["source_workbook"] == "opening_inventory_valid.csv"
    assert rows[0]["source_sheet"] == "CSV"
    assert rows[0]["source_row_number"] == 2
    assert rows[0]["raw_seller_code"] == "SELLER-001"
    assert rows[0]["raw_sku"] == "SKU-001"
    assert rows[0]["raw_upc"] == "012345678905"
    assert rows[0]["raw_location_code"] == "A-01"
    assert rows[0]["raw_quantity"] == "25.00"


def test_parse_opening_inventory_csv_skips_empty_rows() -> None:
    """Verify fully blank CSV rows are skipped."""
    file_bytes = (
        b"seller_code,sku,warehouse_code,inventory_state,quantity\n"
        b"\n"
        b"SELLER-001,SKU-001,RENO,AVAILABLE,1.00\n"
    )

    rows = parse_opening_inventory_csv("blank_rows.csv", file_bytes)

    assert len(rows) == 1
    assert rows[0]["source_row_number"] == 3


def test_parse_opening_inventory_file_rejects_unsupported_extension() -> None:
    """Verify unsupported source file types are rejected."""
    with pytest.raises(ValueError, match="Unsupported opening inventory file type"):
        parse_opening_inventory_file("opening_inventory.txt", b"not supported")


def test_parse_opening_inventory_csv_requires_expected_columns() -> None:
    """Verify missing required migration columns are rejected."""
    file_bytes = b"seller_code,sku,quantity\nSELLER-001,SKU-001,1.00\n"

    with pytest.raises(ValueError, match="Missing required opening inventory columns"):
        parse_opening_inventory_csv("missing_columns.csv", file_bytes)


def test_opening_inventory_row_hash_is_deterministic() -> None:
    """Verify source hashes are deterministic for equivalent raw rows."""
    row = {
        "source_workbook": "stock.csv",
        "source_sheet": "CSV",
        "source_row_number": 2,
        "raw_seller_code": "SELLER-001",
        "raw_sku": "SKU-001",
        "raw_upc": None,
        "raw_warehouse_code": "RENO",
        "raw_location_code": None,
        "raw_inventory_state": "AVAILABLE",
        "raw_quantity": "10.00",
    }

    assert compute_opening_inventory_row_hash(row) == compute_opening_inventory_row_hash(dict(row))


def test_parse_opening_inventory_xlsx_when_openpyxl_available() -> None:
    """Verify XLSX parsing when the optional openpyxl dependency is installed."""
    pytest.importorskip("openpyxl")
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Opening"
    sheet.append(
        [
            "seller_code",
            "sku",
            "warehouse_code",
            "location_code",
            "inventory_state",
            "quantity",
        ]
    )
    sheet.append(["SELLER-001", "SKU-001", "RENO", "A-01", "AVAILABLE", "5.00"])

    buffer = BytesIO()
    workbook.save(buffer)
    workbook.close()

    rows = parse_opening_inventory_xlsx("opening.xlsx", buffer.getvalue())

    assert len(rows) == 1
    assert rows[0]["source_workbook"] == "opening.xlsx"
    assert rows[0]["source_sheet"] == "Opening"
    assert rows[0]["source_row_number"] == 2
    assert rows[0]["raw_quantity"] == "5.00"
