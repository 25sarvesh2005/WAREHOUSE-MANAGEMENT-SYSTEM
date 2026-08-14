/*
--------------------------------------------------------------------------------
File        : frontend/src/lib/offline-receipt-store.ts
Purpose     : Offline IndexedDB draft queue for receiving receipts.

Responsibilities:
    - Save local receipt drafts when offline or network calls fail.
    - Assign unique client_draft_id idempotency UUID per draft.
    - Maintain draft sync state: DRAFT, PENDING_SYNC, SYNCED, CONFLICT.
    - Replay pending offline drafts to backend API when online.
    - Migrate legacy localStorage drafts into IndexedDB once.
--------------------------------------------------------------------------------
*/

import { createReceiptApi, saveReceiptLineApi } from "./api-services";

export interface OfflineReceiptLine {
  id: string;
  product_id: string;
  product_sku?: string;
  expected_quantity: number;
  sellable_quantity: number;
  damaged_quantity: number;
  quarantined_quantity: number;
  notes?: string;
}

export interface OfflineDraftReceipt {
  id: string;
  client_draft_id: string;
  seller_id: string;
  warehouse_id: string;
  source_type: string;
  source_reference: string;
  lines: OfflineReceiptLine[];
  syncStatus: "DRAFT" | "PENDING_SYNC" | "SYNCED" | "CONFLICT";
  syncError?: string;
  created_at: string;
}

const DATABASE_NAME = "whitfield_offline_receipts";
const DATABASE_VERSION = 1;
const RECEIPT_STORE_NAME = "receipt_drafts";
const LEGACY_STORAGE_KEY = "whitfield_offline_receipt_drafts_v1";

type DraftInput = Omit<
  OfflineDraftReceipt,
  "id" | "client_draft_id" | "syncStatus" | "created_at"
> & {
  id?: string;
  client_draft_id?: string;
};

function getIndexedDb(): IDBFactory | null {
  if (typeof window === "undefined" || !window.indexedDB) return null;
  return window.indexedDB;
}

function requestToPromise<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("IndexedDB request failed."));
  });
}

function openDatabase(): Promise<IDBDatabase> {
  const indexedDb = getIndexedDb();
  if (!indexedDb) {
    return Promise.reject(new Error("IndexedDB is not available in this browser."));
  }

  return new Promise((resolve, reject) => {
    const request = indexedDb.open(DATABASE_NAME, DATABASE_VERSION);

    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(RECEIPT_STORE_NAME)) {
        const store = database.createObjectStore(RECEIPT_STORE_NAME, { keyPath: "id" });
        store.createIndex("client_draft_id", "client_draft_id", { unique: true });
        store.createIndex("syncStatus", "syncStatus", { unique: false });
        store.createIndex("created_at", "created_at", { unique: false });
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("Could not open IndexedDB."));
  });
}

async function withDraftStore<T>(
  mode: IDBTransactionMode,
  operation: (store: IDBObjectStore) => IDBRequest<T>,
): Promise<T> {
  const database = await openDatabase();
  try {
    const transaction = database.transaction(RECEIPT_STORE_NAME, mode);
    const store = transaction.objectStore(RECEIPT_STORE_NAME);
    return await requestToPromise(operation(store));
  } finally {
    database.close();
  }
}

async function migrateLegacyLocalStorageDrafts(): Promise<void> {
  if (typeof localStorage === "undefined") return;

  const rawDrafts = localStorage.getItem(LEGACY_STORAGE_KEY);
  if (!rawDrafts) return;

  try {
    const drafts = JSON.parse(rawDrafts) as OfflineDraftReceipt[];
    for (const draft of drafts) {
      await withDraftStore("readwrite", (store) => store.put(draft));
    }
    localStorage.removeItem(LEGACY_STORAGE_KEY);
  } catch (error) {
    console.error("Failed to migrate legacy offline receipt drafts:", error);
  }
}

export function generateUUID(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (character) => {
    const randomNibble = (Math.random() * 16) | 0;
    const value = character === "x" ? randomNibble : (randomNibble & 0x3) | 0x8;
    return value.toString(16);
  });
}

export async function saveOfflineDraft(draft: DraftInput): Promise<OfflineDraftReceipt> {
  await migrateLegacyLocalStorageDrafts();

  const fullDraft: OfflineDraftReceipt = {
    id: draft.id || generateUUID(),
    client_draft_id: draft.client_draft_id || generateUUID(),
    seller_id: draft.seller_id,
    warehouse_id: draft.warehouse_id,
    source_type: draft.source_type,
    source_reference: draft.source_reference,
    lines: draft.lines || [],
    syncStatus: "PENDING_SYNC",
    created_at: new Date().toISOString(),
  };

  await withDraftStore("readwrite", (store) => store.put(fullDraft));
  return fullDraft;
}

export async function getOfflineDrafts(): Promise<OfflineDraftReceipt[]> {
  await migrateLegacyLocalStorageDrafts();
  return withDraftStore("readonly", (store) => store.getAll());
}

export async function removeOfflineDraft(id: string): Promise<void> {
  await withDraftStore("readwrite", (store) => store.delete(id));
}

async function updateOfflineDraft(draft: OfflineDraftReceipt): Promise<void> {
  await withDraftStore("readwrite", (store) => store.put(draft));
}

export async function syncOfflineDrafts(): Promise<{
  syncedCount: number;
  conflictCount: number;
  failedCount: number;
}> {
  const drafts = await getOfflineDrafts();
  const pending = drafts.filter(
    (draft) => draft.syncStatus === "PENDING_SYNC" || draft.syncStatus === "CONFLICT",
  );

  let syncedCount = 0;
  let conflictCount = 0;
  let failedCount = 0;

  for (const draft of pending) {
    try {
      const serverReceipt = await createReceiptApi({
        seller_id: draft.seller_id,
        warehouse_id: draft.warehouse_id,
        source_type: draft.source_type,
        source_reference: draft.source_reference,
        client_draft_id: draft.client_draft_id,
      });

      for (const line of draft.lines) {
        await saveReceiptLineApi(serverReceipt.id, {
          product_id: line.product_id,
          expected_quantity: line.expected_quantity,
          sellable_quantity: line.sellable_quantity,
          damaged_quantity: line.damaged_quantity,
          quarantined_quantity: line.quarantined_quantity,
          ...(line.notes ? { notes: line.notes } : {}),
        });
      }

      syncedCount += 1;
      await removeOfflineDraft(draft.id);
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : "Sync failed";
      if (
        errorMessage.includes("409") ||
        errorMessage.toLowerCase().includes("conflict") ||
        errorMessage.toLowerCase().includes("duplicate")
      ) {
        await updateOfflineDraft({
          ...draft,
          syncStatus: "CONFLICT",
          syncError: "Duplicate tracking reference exists on server.",
        });
        conflictCount += 1;
      } else {
        await updateOfflineDraft({
          ...draft,
          syncStatus: "PENDING_SYNC",
          syncError: errorMessage,
        });
        failedCount += 1;
      }
    }
  }

  return { syncedCount, conflictCount, failedCount };
}
