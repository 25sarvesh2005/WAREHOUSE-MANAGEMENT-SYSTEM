"""
Model Context Protocol (MCP) server application and endpoint dispatcher.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import APIRouter, Header, HTTPException, Request, Response, status

from common.auth import decode_access_token
from common.logger import get_logger
from core.database.database import close_database_connection, connect_to_database
from mcp_server.context import RequesterContext
from mcp_server.tools import MCP_TOOLS, MCPRecordNotFoundError, MCPScopeViolationError, MCPToolError

logger = get_logger(__name__)

mcp_router = APIRouter(prefix="/mcp", tags=["Model Context Protocol"])


@mcp_router.get("", summary="MCP Server Capabilities & Tools Catalog")
@mcp_router.get("/", summary="MCP Server Capabilities & Tools Catalog")
async def list_mcp_tools(
    authorization: str | None = Header(None, description="Bearer <JWT_TOKEN>"),
) -> dict[str, Any]:
    """
    List available read-only MCP operational tools and input schemas.
    """
    return {
        "protocol_version": "2024-11-05",
        "server": {
            "name": "whitfield-warehouse-mcp",
            "version": "0.1.0",
            "description": "Whitfield Fulfillment warehouse operations read-only tools.",
        },
        "tools": [
            {
                "name": "inventory_lookup",
                "description": "Look up available inventory stock balances for a SKU or product name grouped by warehouse.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "sku": {"type": "string", "description": "Product SKU or product name to search"},
                    },
                    "required": ["sku"],
                },
            },
            {
                "name": "ledger_explanation",
                "description": "Retrieve append-only inventory movement ledger history for an audit explanation.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "sku": {"type": "string", "description": "Product SKU to retrieve history for"},
                        "limit": {"type": "integer", "description": "Max movement records (default 10)", "default": 10},
                    },
                    "required": ["sku"],
                },
            },
            {
                "name": "order_status",
                "description": "Query the status and fulfillment lines of a customer order.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "reference_number": {"type": "string", "description": "Seller order reference number"},
                        "order_id": {"type": "string", "description": "Internal order UUID"},
                    },
                },
            },
            {
                "name": "receipt_status",
                "description": "Query the status and line dispositions of an inbound receiving receipt.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "receipt_number": {"type": "string", "description": "Inbound receipt number"},
                        "receipt_id": {"type": "string", "description": "Internal receipt UUID"},
                    },
                },
            },
            {
                "name": "transfer_status",
                "description": "Query status and line progress of an inter-warehouse inventory transfer.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "transfer_number": {"type": "string", "description": "Transfer order reference number"},
                        "transfer_id": {"type": "string", "description": "Internal transfer UUID"},
                    },
                },
            },
            {
                "name": "shipment_status",
                "description": "Query tracking status and package contents of an outbound fulfillment shipment.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tracking_number": {"type": "string", "description": "Carrier tracking number"},
                        "shipment_id": {"type": "string", "description": "Internal shipment UUID"},
                    },
                },
            },
            {
                "name": "return_status",
                "description": "Query receipt and inspection disposition status of a customer return.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "return_number": {"type": "string", "description": "Return RMA or return number"},
                        "return_id": {"type": "string", "description": "Internal return UUID"},
                    },
                },
            },
            {
                "name": "exception_listing",
                "description": "Query operational exception records across warehouse subsystems.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ],
    }


@mcp_router.post("/call", summary="Execute an MCP Tool")
async def call_mcp_tool(
    request: Request,
    authorization: str | None = Header(None, description="Bearer <JWT_TOKEN>"),
) -> dict[str, Any]:
    """
    Execute a registered MCP tool under caller permissions.

    Expects JSON payload: `{"name": "tool_name", "arguments": { ... }}`
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization Bearer header",
        )

    token = authorization.split("Bearer ", 1)[1].strip()
    try:
        requester = RequesterContext.from_jwt_token(token)
    except Exception as auth_err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        ) from auth_err

    body = await request.json()
    tool_name = body.get("name")
    tool_args = body.get("arguments", {})

    if not tool_name or tool_name not in MCP_TOOLS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown tool: {tool_name}",
        )

    tool_func = MCP_TOOLS[tool_name]
    try:
        # Pass requester and kwargs
        result = await tool_func(requester=requester, **tool_args)
        return {
            "content": [
                {
                    "type": "text",
                    "data": result,
                }
            ],
            "isError": False,
        }
    except (MCPScopeViolationError, MCPRecordNotFoundError) as domain_err:
        return {
            "content": [{"type": "text", "data": str(domain_err)}],
            "isError": True,
        }
    except MCPToolError as tool_err:
        return {
            "content": [{"type": "text", "data": str(tool_err)}],
            "isError": True,
        }
    except TypeError as arg_err:
        return {
            "content": [{"type": "text", "data": f"Invalid tool arguments: {arg_err}"}],
            "isError": True,
        }
    except Exception as unexpected:
        logger.error("Unexpected error executing MCP tool %s: %s", tool_name, unexpected, exc_info=True)
        return {
            "content": [{"type": "text", "data": "Internal error executing tool"}],
            "isError": True,
        }


@asynccontextmanager
async def mcp_lifespan(app_instance: Any) -> AsyncIterator[None]:
    """Lifespan manager when running MCP as a standalone ASGI process."""
    await connect_to_database()
    try:
        yield
    finally:
        await close_database_connection()


def create_mcp_server():
    """Factory to create a standalone FastAPI application hosting MCP."""
    from fastapi import FastAPI
    app = FastAPI(
        title="Whitfield Warehouse MCP Server",
        description="Model Context Protocol Server for warehouse visibility.",
        version="0.1.0",
        lifespan=mcp_lifespan,
    )
    app.include_router(mcp_router)
    return app


mcp_app = create_mcp_server
