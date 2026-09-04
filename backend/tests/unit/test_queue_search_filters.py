"""
Unit Tests for Server-Backed Queue Search, Filtering, and Pagination.

Proves SQL predicate generation, case-insensitivity, wildcard escaping, and query scoping
for both multi-warehouse transfers and customer returns without hitting an external database.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.sql.selectable import Select

from core.cruds import return_crud, transfer_crud


@pytest.fixture(autouse=True)
async def ensure_db() -> Any:
    """Bypass external database connection for unit tests that compile SQL without DB access."""
    yield None


class MockExecutionResult:
    """Mock execution result providing scalar and scalars helpers for SQLAlchemy statements."""

    def __init__(self, scalar_value: Any = 1, scalars_value: list[Any] | None = None) -> None:
        """Initialize mock execution result."""
        self._scalar_value = scalar_value
        self._scalars_value = scalars_value or []

    def scalar(self) -> Any:
        """Return mock scalar integer count."""
        return self._scalar_value

    def scalars(self) -> MockExecutionResult:
        """Return self to chain all() method."""
        return self

    def all(self) -> list[Any]:
        """Return mock list of entity records."""
        return self._scalars_value


class StatementCapturingSession:
    """Mock async session capturing executed statements for SQL and parameter assertions."""

    def __init__(self) -> None:
        """Initialize empty statement capture list."""
        self.statements: list[Select] = []

    async def execute(self, stmt: Any) -> MockExecutionResult:
        """Capture statement and return mock execution result."""
        self.statements.append(stmt)
        return MockExecutionResult(scalar_value=1, scalars_value=[])


def compile_statement(stmt: Select) -> tuple[str, dict[str, Any]]:
    """
    Compile a SQLAlchemy statement to dialect-neutral string and bound parameter dictionary.

    Args:
        stmt: SQLAlchemy Select statement.

    Returns:
        tuple[str, dict[str, Any]]: Lowercase compiled SQL and parameter dictionary.
    """
    compiled = stmt.compile(compile_kwargs={"literal_binds": False})
    return str(compiled).lower(), compiled.params


@pytest.mark.asyncio
async def test_transfer_search_case_insensitive_predicate() -> None:
    """Verify that transfer search applies a case-insensitive search predicate on transfer_number and notes."""
    session = StatementCapturingSession()
    await transfer_crud.list_transfers(session, q="TRF-ALPHA")

    assert len(session.statements) == 2
    count_sql, count_params = compile_statement(session.statements[0])
    item_sql, item_params = compile_statement(session.statements[1])

    # Case-insensitive predicate checks both transfer_number and notes
    assert "transfers.transfer_number" in item_sql
    assert "transfers.notes" in item_sql
    assert "like" in item_sql or "ilike" in item_sql

    # Value is enclosed with wildcards
    search_param_values = list(item_params.values())
    assert "%TRF-ALPHA%" in search_param_values


@pytest.mark.asyncio
async def test_transfer_search_applied_to_item_and_count_queries() -> None:
    """Verify that transfer search is applied to both the item query and the count query."""
    session = StatementCapturingSession()
    await transfer_crud.list_transfers(session, q="EXPEDITED")

    assert len(session.statements) == 2
    count_sql, count_params = compile_statement(session.statements[0])
    item_sql, item_params = compile_statement(session.statements[1])

    assert "transfers.transfer_number" in count_sql
    assert "transfers.notes" in count_sql
    assert "%EXPEDITED%" in list(count_params.values())

    assert "transfers.transfer_number" in item_sql
    assert "transfers.notes" in item_sql
    assert "%EXPEDITED%" in list(item_params.values())


@pytest.mark.asyncio
async def test_return_search_covers_number_rma_tracking() -> None:
    """Verify that return search covers return number, RMA number, and inbound tracking number."""
    session = StatementCapturingSession()
    await return_crud.list_returns(session, q="RET-QUERY-123")

    assert len(session.statements) == 2
    item_sql, item_params = compile_statement(session.statements[1])

    assert "returns.return_number" in item_sql
    assert "returns.rma_number" in item_sql
    assert "returns.inbound_tracking_number" in item_sql
    assert "%RET-QUERY-123%" in list(item_params.values())


@pytest.mark.asyncio
async def test_return_search_applied_to_item_and_count_queries() -> None:
    """Verify that return search is applied to both item and count statements."""
    session = StatementCapturingSession()
    await return_crud.list_returns(session, q="TRACK987")

    assert len(session.statements) == 2
    count_sql, count_params = compile_statement(session.statements[0])
    item_sql, item_params = compile_statement(session.statements[1])

    for sql, params in [(count_sql, count_params), (item_sql, item_params)]:
        assert "returns.return_number" in sql
        assert "returns.rma_number" in sql
        assert "returns.inbound_tracking_number" in sql
        assert "%TRACK987%" in list(params.values())


@pytest.mark.asyncio
async def test_search_wildcards_escaped_literally() -> None:
    """Verify that %, _, and \\ characters are escaped rather than treated as SQL wildcards."""
    session = StatementCapturingSession()

    # Transfers
    await transfer_crud.list_transfers(session, q="10%_TRF\\01")
    _, transfer_params = compile_statement(session.statements[1])
    # Escaped pattern: %10\%\_TRF\\01%
    assert "%10\\%\\_TRF\\\\01%" in list(transfer_params.values())

    # Returns
    session.statements.clear()
    await return_crud.list_returns(session, q="25%_RMA\\99")
    _, return_params = compile_statement(session.statements[1])
    assert "%25\\%\\_RMA\\\\99%" in list(return_params.values())


@pytest.mark.asyncio
async def test_blank_search_behaves_like_no_search() -> None:
    """Verify that blank or whitespace-only search string behaves like no search."""
    session = StatementCapturingSession()

    for blank_val in ["", "   ", "\t\n"]:
        session.statements.clear()
        await transfer_crud.list_transfers(session, q=blank_val)
        count_sql, count_params = compile_statement(session.statements[0])
        item_sql, item_params = compile_statement(session.statements[1])
        assert "where" not in count_sql
        assert "like" not in item_sql
        assert "ilike" not in item_sql
        assert len(item_params) == 2  # Only limit and offset

        session.statements.clear()
        await return_crud.list_returns(session, q=blank_val)
        count_sql, count_params = compile_statement(session.statements[0])
        ret_sql, ret_params = compile_statement(session.statements[1])
        assert "where" not in count_sql
        assert "like" not in ret_sql
        assert "ilike" not in ret_sql
        assert len(ret_params) == 2  # Only limit and offset


@pytest.mark.asyncio
async def test_search_combines_with_existing_filters() -> None:
    """Verify that seller, facility, and status filters remain combined with search using AND predicates."""
    session = StatementCapturingSession()
    seller_uuid = uuid4()
    origin_wh_uuid = uuid4()
    dest_wh_uuid = uuid4()

    await transfer_crud.list_transfers(
        session,
        q="TRANSFER-NOTE",
        seller_id=seller_uuid,
        origin_warehouse_id=origin_wh_uuid,
        destination_warehouse_id=dest_wh_uuid,
        status="APPROVED",
    )

    item_sql, item_params = compile_statement(session.statements[1])
    assert "transfers.seller_id ==" in item_sql or "transfers.seller_id =" in item_sql
    assert "transfers.origin_warehouse_id ==" in item_sql or "transfers.origin_warehouse_id =" in item_sql
    assert "transfers.destination_warehouse_id ==" in item_sql or "transfers.destination_warehouse_id =" in item_sql
    assert "transfers.status ==" in item_sql or "transfers.status =" in item_sql
    assert "transfers.transfer_number" in item_sql
    assert "%TRANSFER-NOTE%" in list(item_params.values())

    # Test returns combination
    session.statements.clear()
    await return_crud.list_returns(
        session,
        q="RMA-ACTIVE",
        seller_id=seller_uuid,
        warehouse_id=origin_wh_uuid,
        status="INSPECTION",
    )
    ret_sql, ret_params = compile_statement(session.statements[1])
    assert "returns.seller_id ==" in ret_sql or "returns.seller_id =" in ret_sql
    assert "returns.warehouse_id ==" in ret_sql or "returns.warehouse_id =" in ret_sql
    assert "returns.status ==" in ret_sql or "returns.status =" in ret_sql
    assert "returns.return_number" in ret_sql
    assert "%RMA-ACTIVE%" in list(ret_params.values())


@pytest.mark.asyncio
async def test_limit_and_offset_applied_to_item_query_only() -> None:
    """Verify that limit and offset remain applied to the item query and omitted from the count query."""
    session = StatementCapturingSession()
    await transfer_crud.list_transfers(session, limit=25, offset=50)

    assert len(session.statements) == 2
    count_sql, count_params = compile_statement(session.statements[0])
    item_sql, item_params = compile_statement(session.statements[1])

    assert "limit" not in count_sql
    assert "offset" not in count_sql

    assert "limit" in item_sql
    assert "offset" in item_sql
    assert 25 in list(item_params.values())
    assert 50 in list(item_params.values())
