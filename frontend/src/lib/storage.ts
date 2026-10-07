/**
 * Resilient cross-environment storage wrapper.
 * Safely falls back to an in-memory Map if `window.localStorage` throws
 * a SecurityError, DOMException, or is unavailable in restricted/sandboxed environments.
 */
class SafeStorage {
  private memory = new Map<string, string>();

  private getStorage(): Storage | null {
    if (typeof window === "undefined") return null;
    try {
      const storage = window.localStorage;
      if (!storage) return null;
      const testKey = "__wms_storage_test__";
      storage.setItem(testKey, testKey);
      storage.removeItem(testKey);
      return storage;
    } catch {
      return null;
    }
  }

  getItem(key: string): string | null {
    try {
      const storage = this.getStorage();
      if (storage) return storage.getItem(key);
    } catch {
      // Silently fall through to memory fallback
    }
    return this.memory.get(key) ?? null;
  }

  setItem(key: string, value: string): void {
    try {
      const storage = this.getStorage();
      if (storage) {
        storage.setItem(key, value);
        return;
      }
    } catch {
      // Silently fall through to memory fallback
    }
    this.memory.set(key, value);
  }

  removeItem(key: string): void {
    try {
      const storage = this.getStorage();
      if (storage) {
        storage.removeItem(key);
      }
    } catch {
      // Silently fall through to memory fallback
    }
    this.memory.delete(key);
  }
}

export const safeStorage = new SafeStorage();
