"""
Security context and authorization models for Model Context Protocol (MCP) clients.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from common.auth import decode_access_token
from common.logger import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class RequesterContext:
    """
    Caller identity and tenant permission scope for MCP tool execution.

    Enforces seller and warehouse boundaries identical to API controller access.
    """

    user_id: UUID
    email: str
    role: str
    seller_id: UUID | None = None
    seller_ids: list[UUID] = field(default_factory=list)
    warehouse_id: UUID | None = None
    warehouse_ids: list[UUID] = field(default_factory=list)
    raw_token: str | None = None

    @classmethod
    def from_jwt_token(cls, token: str) -> RequesterContext:
        """
        Build RequesterContext from a signed JWT bearer token.

        Args:
            token: Raw Bearer JWT token string.

        Returns:
            RequesterContext: Validated requester context.
        """
        payload = decode_access_token(token)
        return cls.from_dict(payload, raw_token=token)

    @classmethod
    def from_dict(cls, data: dict[str, Any], raw_token: str | None = None) -> RequesterContext:
        """
        Build RequesterContext from a decoded JWT payload or session scope dictionary.

        Args:
            data: Decoded claims containing user_id, email, role, etc.
            raw_token: Optional original bearer token.

        Returns:
            RequesterContext: Normalized context.
        """
        user_id = UUID(str(data["user_id"]))
        email = str(data.get("email", ""))
        role = str(data.get("role", ""))

        seller_id_raw = data.get("seller_id")
        seller_id = UUID(str(seller_id_raw)) if seller_id_raw else None

        seller_ids: list[UUID] = []
        for s in data.get("seller_ids", []):
            try:
                seller_ids.append(UUID(str(s)))
            except (ValueError, TypeError):
                pass
        if seller_id and seller_id not in seller_ids:
            seller_ids.append(seller_id)

        warehouse_id_raw = data.get("warehouse_id")
        warehouse_id = UUID(str(warehouse_id_raw)) if warehouse_id_raw else None

        warehouse_ids: list[UUID] = []
        for w in data.get("warehouse_ids", []):
            try:
                warehouse_ids.append(UUID(str(w)))
            except (ValueError, TypeError):
                pass
        if warehouse_id and warehouse_id not in warehouse_ids:
            warehouse_ids.append(warehouse_id)

        return cls(
            user_id=user_id,
            email=email,
            role=role,
            seller_id=seller_id,
            seller_ids=seller_ids,
            warehouse_id=warehouse_id,
            warehouse_ids=warehouse_ids,
            raw_token=raw_token,
        )

    def to_scope_dict(self) -> dict[str, Any]:
        """Convert to standard controller scope dictionary."""
        return {
            "user_id": str(self.user_id),
            "email": self.email,
            "role": self.role,
            "seller_id": str(self.seller_id) if self.seller_id else None,
            "seller_ids": [str(s) for s in self.seller_ids],
            "warehouse_id": str(self.warehouse_id) if self.warehouse_id else None,
            "warehouse_ids": [str(w) for w in self.warehouse_ids],
        }
