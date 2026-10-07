import { safeStorage } from "./storage";
import type { User } from "./types";

export const TOKEN_KEY = "whitfield_access_token";
export const REFRESH_TOKEN_KEY = "whitfield_refresh_token";
const USER_KEY = "whitfield_user";

export function readAccessToken(): string | null {
  return safeStorage.getItem(TOKEN_KEY);
}

export function readRefreshToken(): string | null {
  return safeStorage.getItem(REFRESH_TOKEN_KEY);
}

export function storeTokens(accessToken: string, refreshToken?: string): void {
  safeStorage.setItem(TOKEN_KEY, accessToken);
  if (refreshToken) {
    safeStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  }
}

export function storeUser(user: User): void {
  safeStorage.setItem(USER_KEY, JSON.stringify(user));
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event("whitfield-auth"));
  }
}

export function readUser(): User | null {
  if (!readAccessToken()) return null;
  try {
    const raw = safeStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as User) : null;
  } catch {
    return null;
  }
}

export function clearSession(): void {
  safeStorage.removeItem(TOKEN_KEY);
  safeStorage.removeItem(REFRESH_TOKEN_KEY);
  safeStorage.removeItem(USER_KEY);
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event("whitfield-auth"));
  }
}
