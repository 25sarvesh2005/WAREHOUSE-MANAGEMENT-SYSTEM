"""
--------------------------------------------------------------------------------
File        : tests/unit/test_master_data_flows.py
Purpose     : Test master data controllers and request/response schemas.

Responsibilities:
    - Validate product, location, and policy request schema bounds.
    - Validate master data schema serialization.

Flow:
    pytest
        ->
    Master data schema validation
        ->
    Assertion

Used By:
    - pytest

Returns:
    test_*() -> None - Pytest assertions.

Raises:
    AssertionError: When master data validation regresses.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from core.apis.schemas.requests.catalog_request import (
    ProductCreateRequest,
    ProductIdentifierCreateRequest,
    SellerOrderPolicyCreateRequest,
    WarehouseLocationCreateRequest,
)
from core.apis.schemas.requests.identity_request import (
    SellerCreateRequest,
    SellerStatusUpdateRequest,
    UserCreateRequest,
    UserStatusUpdateRequest,
    WarehouseCreateRequest,
)
from core.constants import (
    AllocationStrategy,
    BusinessStatus,
    ProductIdentifierType,
    UserRole,
    UserStatus,
    WarehouseLocationType,
)


def test_user_create_request_validation() -> None:
    """
    Verify UserCreateRequest accepts valid fields and normalizes emails.

    Returns:
        None.

    Raises:
        AssertionError: If validation fails.
    """
    req = UserCreateRequest(
        email="operator@whitfield.local",
        name="Test Operator",
        password="SecurePassword123!",
        role=UserRole.RECEIVER,
    )
    assert req.email == "operator@whitfield.local"
    assert req.name == "Test Operator"
    assert req.role == UserRole.RECEIVER


def test_seller_create_request_validation() -> None:
    """
    Verify SellerCreateRequest validates codes and normalizes optional email.

    Returns:
        None.

    Raises:
        AssertionError: If validation fails.
    """
    req = SellerCreateRequest(
        code="SELLER-01",
        name="Acme Fulfillment Corp",
        contact_email="contact@acme.local",
    )
    assert req.code == "SELLER-01"
    assert req.name == "Acme Fulfillment Corp"
    assert req.status == BusinessStatus.ACTIVE


def test_warehouse_create_request_validation() -> None:
    """
    Verify WarehouseCreateRequest validates warehouse codes and default timezone.

    Returns:
        None.

    Raises:
        AssertionError: If validation fails.
    """
    req = WarehouseCreateRequest(
        code="PDX",
        name="Portland Fulfillment Warehouse",
        city="Portland",
        state="Oregon",
    )
    assert req.code == "PDX"
    assert req.timezone == "America/Los_Angeles"


def test_product_create_request_validation() -> None:
    """
    Verify ProductCreateRequest validates SKU format and default unit of measure.

    Returns:
        None.

    Raises:
        AssertionError: If validation fails.
    """
    seller_id = uuid4()
    req = ProductCreateRequest(
        seller_id=seller_id,
        sku="SKU-1001-TEST",
        name="Widget Model A",
    )
    assert req.seller_id == seller_id
    assert req.sku == "SKU-1001-TEST"
    assert req.unit_of_measure == "EA"


def test_product_identifier_request_validation() -> None:
    """
    Verify ProductIdentifierCreateRequest validates identifier types.

    Returns:
        None.

    Raises:
        AssertionError: If validation fails.
    """
    product_id = uuid4()
    req = ProductIdentifierCreateRequest(
        product_id=product_id,
        identifier_type=ProductIdentifierType.UPC,
        identifier_value="012345678905",
    )
    assert req.product_id == product_id
    assert req.identifier_type == ProductIdentifierType.UPC
    assert req.identifier_value == "012345678905"


def test_warehouse_location_request_validation() -> None:
    """
    Verify WarehouseLocationCreateRequest validates location types.

    Returns:
        None.

    Raises:
        AssertionError: If validation fails.
    """
    wh_id = uuid4()
    req = WarehouseLocationCreateRequest(
        warehouse_id=wh_id,
        code="REC-01-A",
        location_type=WarehouseLocationType.RECEIVING,
    )
    assert req.warehouse_id == wh_id
    assert req.code == "REC-01-A"
    assert req.location_type == WarehouseLocationType.RECEIVING


def test_seller_order_policy_request_validation() -> None:
    """
    Verify SellerOrderPolicyCreateRequest validates policy fields and strategies.

    Returns:
        None.

    Raises:
        AssertionError: If validation fails.
    """
    seller_id = uuid4()
    req = SellerOrderPolicyCreateRequest(
        seller_id=seller_id,
        allow_backorder=False,
        allow_partial_fulfillment=True,
        reservation_expiry_minutes=120,
        allocation_strategy=AllocationStrategy.FIFO,
    )
    assert req.seller_id == seller_id
    assert req.allow_backorder is False
    assert req.allow_partial_fulfillment is True
    assert req.reservation_expiry_minutes == 120
    assert req.allocation_strategy == AllocationStrategy.FIFO


def test_user_and_seller_status_update_schemas() -> None:
    """
    Verify UserStatusUpdateRequest and SellerStatusUpdateRequest enforce valid domain statuses.
    """
    user_status_req = UserStatusUpdateRequest(status=UserStatus.ACTIVE)
    assert user_status_req.status == UserStatus.ACTIVE

    user_suspended_req = UserStatusUpdateRequest(status=UserStatus.SUSPENDED)
    assert user_suspended_req.status == UserStatus.SUSPENDED

    seller_status_req = SellerStatusUpdateRequest(status=BusinessStatus.ACTIVE)
    assert seller_status_req.status == BusinessStatus.ACTIVE

    seller_inactive_req = SellerStatusUpdateRequest(status=BusinessStatus.INACTIVE)
    assert seller_inactive_req.status == BusinessStatus.INACTIVE

