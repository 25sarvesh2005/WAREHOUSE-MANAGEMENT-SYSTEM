import type { Page } from "@playwright/test";

export const MOCK_ADMIN_USER = {
  id: "00000000-0000-0000-0000-000000000001",
  user_id: "00000000-0000-0000-0000-000000000001",
  email: "admin@whitfield.local",
  name: "System Admin",
  role: "ADMINISTRATOR" as const,
  status: "ACTIVE",
  seller_ids: [],
  warehouse_ids: ["00000000-0000-0000-0000-000000000002"],
};

export const MOCK_TOKENS = {
  access_token: "mock-valid-jwt-token-for-e2e-testing",
  refresh_token: "mock-valid-refresh-token-for-e2e-testing",
  token_type: "bearer",
};

/**
 * Injects mock authentication session into localStorage so tests start in authenticated state.
 */
export async function injectAuthSession(page: Page, user = MOCK_ADMIN_USER) {
  await page.addInitScript(
    ({ user, tokens }) => {
      window.localStorage.setItem("whitfield_access_token", tokens.access_token);
      window.localStorage.setItem("whitfield_refresh_token", tokens.refresh_token);
      window.localStorage.setItem("whitfield_user", JSON.stringify(user));
    },
    { user, tokens: MOCK_TOKENS },
  );
}

/**
 * Clears localStorage so tests start in clean unauthenticated state.
 */
export async function clearAuthSession(page: Page) {
  await page.addInitScript(() => {
    window.localStorage.removeItem("whitfield_access_token");
    window.localStorage.removeItem("whitfield_refresh_token");
    window.localStorage.removeItem("whitfield_user");
  });
}

export const MOCK_TRANSFERS = Array.from({ length: 30 }, (_, i) => {
  const index = i + 1;
  const numStr = String(index).padStart(4, "0");
  const idNum = String(index).padStart(2, "0");
  const id =
    index === 1
      ? "00000000-0000-0000-0000-000000000050"
      : `00000000-0000-0000-0000-0000000000${idNum}`;
  const statuses = ["DRAFT", "PENDING_APPROVAL", "APPROVED", "DISPATCHED", "RECEIVED", "DISCREPANCY_REVIEW"];
  const status = index === 1 ? "DRAFT" : statuses[(index - 1) % statuses.length];
  return {
    id,
    transfer_number: `TRN-2026-${numStr}`,
    origin_warehouse_code: index % 2 === 0 ? "DAL" : "RENO",
    origin_warehouse_id:
      index % 2 === 0
        ? "00000000-0000-0000-0000-000000000003"
        : "00000000-0000-0000-0000-000000000002",
    destination_warehouse_code: index % 2 === 0 ? "RENO" : "DAL",
    destination_warehouse_id:
      index % 2 === 0
        ? "00000000-0000-0000-0000-000000000002"
        : "00000000-0000-0000-0000-000000000003",
    seller_id: "00000000-0000-0000-0000-000000000004",
    status,
    notes: index === 3 ? "Priority restock note" : undefined,
    lines: [
      {
        id: `00000000-0000-0000-0001-0000000000${idNum}`,
        product_id: "00000000-0000-0000-0000-000000000005",
        requested_quantity: 10 + index,
      },
    ],
    created_at: new Date(Date.now() - index * 3600000).toISOString(),
  };
});

export const MOCK_RETURNS = Array.from({ length: 30 }, (_, i) => {
  const index = i + 1;
  const numStr = String(index).padStart(4, "0");
  const idNum = String(index).padStart(2, "0");
  const id =
    index === 1
      ? "00000000-0000-0000-0000-000000000060"
      : `00000000-0000-0000-0002-0000000000${idNum}`;
  const statuses = ["EXPECTED", "INSPECTION", "COMPLETED", "REJECTED"];
  const status = index === 1 ? "EXPECTED" : statuses[(index - 1) % statuses.length];
  return {
    id,
    return_number: `RET-2026-${numStr}`,
    rma_number: `RMA-2026-${numStr}`,
    inbound_tracking_number: `1ZTRACK${numStr}`,
    seller_code: "ALPHA",
    seller_id: "00000000-0000-0000-0000-000000000004",
    warehouse_code: index % 2 === 0 ? "DAL" : "RENO",
    warehouse_id:
      index % 2 === 0
        ? "00000000-0000-0000-0000-000000000003"
        : "00000000-0000-0000-0000-000000000002",
    status,
    notes: index === 5 ? "Return damaged box note" : undefined,
    lines: [],
    created_at: new Date(Date.now() - index * 3600000).toISOString(),
  };
});

/**
 * Standard mock route responder for all primary warehouse resources.
 * Intercepts ONLY API endpoints under /api/v1/ to prevent colliding with Vite frontend source files.
 */
export async function setupStandardApiMocks(page: Page) {
  // Auth endpoints
  await page.route(/\/api\/v1\/auth\/login/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_TOKENS),
    });
  });

  await page.route(/\/api\/v1\/auth\/me/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_ADMIN_USER),
    });
  });

  await page.route(/\/api\/v1\/auth\/logout/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ message: "Successfully logged out" }),
    });
  });

  // Master data
  await page.route(/\/api\/v1\/warehouses/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "00000000-0000-0000-0000-000000000002",
          code: "RENO",
          name: "Reno Fulfillment Center",
          city: "Reno",
          state: "NV",
          utilization: 68,
        },
        {
          id: "00000000-0000-0000-0000-000000000003",
          code: "DAL",
          name: "Dallas Regional DC",
          city: "Dallas",
          state: "TX",
          utilization: 45,
        },
      ]),
    });
  });

  await page.route(/\/api\/v1\/sellers/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "00000000-0000-0000-0000-000000000004",
          code: "ALPHA",
          name: "Alpha Retailer Corp",
          status: "ACTIVE",
        },
      ]),
    });
  });

  await page.route(/\/api\/v1\/products/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "00000000-0000-0000-0000-000000000005",
          seller_id: "00000000-0000-0000-0000-000000000004",
          sku: "SKU-TEST-001",
          name: "Industrial Barcode Scanner",
          unit_of_measure: "EA",
          status: "ACTIVE",
        },
      ]),
    });
  });

  await page.route(/\/api\/v1\/users(?!\/me)/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([MOCK_ADMIN_USER]),
    });
  });

  // Inventory & Dashboard
  await page.route(/\/api\/v1\/inventory\/balances/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "00000000-0000-0000-0000-000000000006",
          product_id: "00000000-0000-0000-0000-000000000005",
          seller_id: "00000000-0000-0000-0000-000000000004",
          warehouse_id: "00000000-0000-0000-0000-000000000002",
          inventory_state: "AVAILABLE",
          quantity: "150.00",
          sku: "SKU-TEST-001",
          seller_code: "ALPHA",
          warehouse_code: "RENO",
          available_quantity: "150.00",
          on_hand_quantity: "180.00",
          allocated_quantity: "30.00",
          damaged_quantity: "0.00",
        },
      ]),
    });
  });

  await page.route(/\/api\/v1\/inventory\/movements/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });

  await page.route(/\/api\/v1\/manager\/dashboard/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        balances_by_state: {
          AVAILABLE: 12500,
          RESERVED: 860,
          DAMAGED: 12,
          QUARANTINED: 8,
          RETURN_INSPECTION: 5,
          IN_TRANSIT: 240,
        },
        open_receipts_count: 3,
        pending_pick_tasks_count: 4,
        active_transfers_count: 2,
        uninspected_returns_count: 1,
      }),
    });
  });

  await page.route(/\/api\/v1\/manager\/exceptions/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        short_pick_exceptions: [
          {
            id: "00000000-0000-0000-0000-000000000031",
            order_id: "00000000-0000-0000-0000-000000000020",
            warehouse_id: "00000000-0000-0000-0000-000000000002",
            status: "SHORT_PICK_EXCEPTION",
            created_at: "2026-01-01T10:00:00.000Z",
          },
        ],
        transfer_discrepancies: [
          {
            id: "00000000-0000-0000-0000-000000000041",
            transfer_number: "TRF-2026-0001",
            origin_warehouse_id: "00000000-0000-0000-0000-000000000002",
            destination_warehouse_id: "00000000-0000-0000-0000-000000000003",
            status: "DISCREPANCY_REVIEW",
          },
        ],
        unidentified_returns: [
          {
            id: "00000000-0000-0000-0000-000000000051",
            return_number: "RET-2026-0001",
            warehouse_id: "00000000-0000-0000-0000-000000000002",
            inbound_tracking_number: "1ZTESTRETURN",
            status: "UNIDENTIFIED",
          },
        ],
      }),
    });
  });

  // Receipts
  await page.route(/\/api\/v1\/receipts/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "00000000-0000-0000-0000-000000000010",
          receipt_number: "REC-2026-0001",
          seller_code: "ALPHA",
          seller_id: "00000000-0000-0000-0000-000000000004",
          warehouse_code: "RENO",
          warehouse_id: "00000000-0000-0000-0000-000000000002",
          status: "STAGED",
          total_lines: 2,
          lines: [],
          created_at: new Date().toISOString(),
        },
      ]),
    });
  });

  // Orders
  await page.route(/\/api\/v1\/orders/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "00000000-0000-0000-0000-000000000020",
          seller_order_number: "ORD-2026-0001",
          order_number: "ORD-2026-0001",
          seller_code: "ALPHA",
          seller_id: "00000000-0000-0000-0000-000000000004",
          warehouse_code: "RENO",
          warehouse_id: "00000000-0000-0000-0000-000000000002",
          status: "PENDING_ALLOCATION",
          customer_name: "Acme Logistics",
          city: "Reno",
          state: "NV",
          created_at: new Date().toISOString(),
          lines: [],
        },
      ]),
    });
  });

  // Pick tasks
  await page.route(/\/api\/v1\/pick-tasks/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "00000000-0000-0000-0000-000000000030",
          task_number: "PICK-2026-0001",
          order_id: "00000000-0000-0000-0000-000000000020",
          order_number: "ORD-2026-0001",
          warehouse_code: "RENO",
          status: "PENDING",
          lines: [],
          created_at: new Date().toISOString(),
        },
      ]),
    });
  });

  // Shipments
  await page.route(/\/api\/v1\/shipments/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "00000000-0000-0000-0000-000000000040",
          shipment_number: "SHP-2026-0001",
          order_id: "00000000-0000-0000-0000-000000000020",
          order_number: "ORD-2026-0001",
          carrier: "FEDEX",
          status: "CREATED",
          packages: [],
          created_at: new Date().toISOString(),
        },
      ]),
    });
  });



  // Transfers
  await page.route(/\/api\/v1\/transfers(?:\?.*)?$/, async (route) => {
    if (route.request().method() !== "GET") {
      await route.continue();
      return;
    }
    const url = new URL(route.request().url());
    const limit = parseInt(url.searchParams.get("limit") || "25", 10);
    const offset = parseInt(url.searchParams.get("offset") || "0", 10);
    const q = url.searchParams.get("q")?.trim().toLowerCase();
    const status = url.searchParams.get("status")?.trim();
    const origin = url.searchParams.get("origin_warehouse_id")?.trim();
    const dest = url.searchParams.get("destination_warehouse_id")?.trim();
    const seller = url.searchParams.get("seller_id")?.trim();

    let items = [...MOCK_TRANSFERS];
    if (q) {
      items = items.filter(
        (t) =>
          t.transfer_number.toLowerCase().includes(q) ||
          (t.notes && t.notes.toLowerCase().includes(q)),
      );
    }
    if (status) {
      items = items.filter((t) => t.status === status);
    }
    if (origin) {
      items = items.filter((t) => t.origin_warehouse_id === origin);
    }
    if (dest) {
      items = items.filter((t) => t.destination_warehouse_id === dest);
    }
    if (seller) {
      items = items.filter((t) => t.seller_id === seller);
    }

    const total = items.length;
    const paginatedItems = items.slice(offset, offset + limit);

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: paginatedItems,
        total,
        limit,
        offset,
      }),
    });
  });

  // Returns
  await page.route(/\/api\/v1\/returns(?:\?.*)?$/, async (route) => {
    if (route.request().method() !== "GET") {
      await route.continue();
      return;
    }
    const url = new URL(route.request().url());
    const limit = parseInt(url.searchParams.get("limit") || "25", 10);
    const offset = parseInt(url.searchParams.get("offset") || "0", 10);
    const q = url.searchParams.get("q")?.trim().toLowerCase();
    const status = url.searchParams.get("status")?.trim();
    const warehouse = url.searchParams.get("warehouse_id")?.trim();
    const seller = url.searchParams.get("seller_id")?.trim();

    let items = [...MOCK_RETURNS];
    if (q) {
      items = items.filter(
        (r) =>
          r.return_number.toLowerCase().includes(q) ||
          (r.rma_number && r.rma_number.toLowerCase().includes(q)) ||
          (r.inbound_tracking_number && r.inbound_tracking_number.toLowerCase().includes(q)),
      );
    }
    if (status) {
      items = items.filter((r) => r.status === status);
    }
    if (warehouse) {
      items = items.filter((r) => r.warehouse_id === warehouse);
    }
    if (seller) {
      items = items.filter((r) => r.seller_id === seller);
    }

    const total = items.length;
    const paginatedItems = items.slice(offset, offset + limit);

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: paginatedItems,
        total,
        limit,
        offset,
      }),
    });
  });

  // Migration
  await page.route(/\/api\/v1\/migration\/batches\/[^/]+\/reconciliation/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        batch_id: "00000000-0000-0000-0000-000000000070",
        batch_number: "MIG-20260814-001",
        reconciliation_status: "RECONCILED",
        total_staged_quantity: "150.00",
        total_ledger_quantity: "150.00",
        total_variance_quantity: "0.00",
        details: [],
      }),
    });
  });

  await page.route(/\/api\/v1\/migration\/batches(?!\/[^/]+\/reconciliation)/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "00000000-0000-0000-0000-000000000070",
          batch_number: "MIG-20260814-001",
          seller_id: "00000000-0000-0000-0000-000000000004",
          warehouse_id: "00000000-0000-0000-0000-000000000002",
          status: "APPLIED",
          total_rows: 15,
          valid_rows: 15,
          invalid_rows: 0,
          created_at: new Date().toISOString(),
        },
      ]),
    });
  });

  // AI Subsystem
  await page.route(/\/api\/v1\/ai\/admin\/provider-health/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        enabled: true,
        provider_name: "google_genai",
        model_name: "gemini-3.1-flash-lite-preview",
        configured: true,
        status: "HEALTHY",
        tested_at: new Date().toISOString(),
      }),
    });
  });

  await page.route(/\/api\/v1\/ai\/admin\/interactions\/[0-9a-fA-F-]+/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "00000000-0000-0000-0000-000000000080",
        actor_user_id: "00000000-0000-0000-0000-000000000001",
        correlation_id: "corr-12345",
        created_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
        request_category: "INVENTORY_AVAILABILITY",
        status: "COMPLETED",
        provider_name: "google_genai",
        model_name: "gemini-3.1-flash-lite-preview",
        prompt_excerpt: "Check availability for SKU-TEST-001 in RENO",
        prompt_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        response_excerpt:
          "SKU-TEST-001 currently has 150 units available at RENO Fulfillment Center.",
        safety_decision: "ALLOW_READ_ONLY",
        refusal_reason: null,
        tool_calls: [
          {
            id: "00000000-0000-0000-0000-000000000090",
            tool_name: "lookup_inventory_availability",
            status: "COMPLETED",
            permission_scope: "READ_ONLY",
            input_excerpt: "sku=SKU-TEST-001, warehouse=RENO",
            output_excerpt: "available_quantity=150.00",
            error_message: null,
            started_at: new Date().toISOString(),
            completed_at: new Date().toISOString(),
          },
        ],
        draft_actions: [],
        feedbacks: [
          {
            feedback_id: "00000000-0000-0000-0000-000000000095",
            is_helpful: true,
            comment: "Accurate count",
            created_at: new Date().toISOString(),
          },
        ],
      }),
    });
  });

  await page.route(/\/api\/v1\/ai\/admin\/interactions(?!\/)/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        total: 1,
        items: [
          {
            id: "00000000-0000-0000-0000-000000000080",
            created_at: new Date().toISOString(),
            request_category: "INVENTORY_AVAILABILITY",
            status: "COMPLETED",
            provider_name: "google_genai",
            prompt_excerpt: "Check availability for SKU-TEST-001 in RENO",
            prompt_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            safety_decision: "ALLOW_READ_ONLY",
            tool_call_count: 1,
            draft_action_count: 0,
            feedback_count: 1,
            helpful_count: 1,
            unhelpful_count: 0,
          },
        ],
      }),
    });
  });

  await page.route(/\/api\/v1\/ai\/drafts/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        total: 0,
        items: [],
      }),
    });
  });

  await page.route(/\/api\/v1\/ai\/inventory\/availability/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        interaction_id: "00000000-0000-0000-0000-000000000080",
        provider_name: "google_genai",
        model_name: "gemini-3.1-flash-lite-preview",
        safety_decision: "ALLOW_READ_ONLY",
        answer: "SKU-TEST-001 currently has 150 units available at RENO Fulfillment Center.",
        rows: [
          {
            sku: "SKU-TEST-001",
            product_name: "Industrial Barcode Scanner",
            seller_code: "ALPHA",
            warehouse_code: "RENO",
            available_quantity: "150.00",
          },
        ],
        references: [
          {
            record_type: "inventory",
            record_id: "00000000-0000-0000-0000-000000000006",
            label: "SKU-TEST-001 @ RENO",
          },
        ],
      }),
    });
  });

  await page.route(/\/api\/v1\/ai\/inventory\/ledger-explanation/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        interaction_id: "00000000-0000-0000-0000-000000000081",
        provider_name: "google_genai",
        model_name: "gemini-3.1-flash-lite-preview",
        safety_decision: "ALLOW_READ_ONLY",
        answer: "Ledger movements show 150 units received under REC-2026-0001.",
        movements: [],
        references: [],
      }),
    });
  });

  await page.route(/\/api\/v1\/ai\/exceptions\/summary/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        interaction_id: "00000000-0000-0000-0000-000000000082",
        provider_name: "google_genai",
        model_name: "gemini-3.1-flash-lite-preview",
        safety_decision: "ALLOW_READ_ONLY",
        answer: "No critical operational exceptions currently detected across network.",
        exceptions: [],
        references: [],
      }),
    });
  });

  await page.route(/\/api\/v1\/ai\/drafts\/recommendation/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        interaction_id: "00000000-0000-0000-0000-000000000083",
        provider_name: "google_genai",
        model_name: "gemini-3.1-flash-lite-preview",
        safety_decision: "DRAFT_ONLY",
        draft_action_id: "00000000-0000-0000-0000-000000000084",
        recommendation_type: "INSPECTION_PRIORITY",
        status: "DRAFT",
        summary: "Prioritize inspection for high-turnover returned goods.",
        details: {},
        references: [],
      }),
    });
  });

  await page.route(/\/api\/v1\/ai\/feedback/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        feedback_id: "00000000-0000-0000-0000-000000000095",
        status: "SAVED",
      }),
    });
  });

  // Operational status report
  await page.route(/(\/api\/v1)?\/health\/status/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "HEALTHY",
        service: "whitfield-warehouse-operations",
        version: "0.1.0",
        app_env: "development",
        database: {
          status: "connected",
          latency_ms: 1.2,
        },
        alembic_head: "c1f2e3d4a5b6",
        ai: {
          status: "HEALTHY",
          provider: "google_genai",
          model: "gemini-3.1-flash-lite-preview",
        },
        warnings: [],
      }),
    });
  });
}
