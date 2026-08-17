import { useEffect, useState } from "react";
import { getCurrentUserApi, loginApi, logoutApi, registerSellerPublicApi } from "./api-services";
import {
  clearSession,
  readRefreshToken,
  readUser as readStoredUser,
  storeTokens,
  storeUser,
} from "./session";
import type { Role, User } from "./types";

export async function signInAsync(email: string, password: string): Promise<User> {
  const tokens = await loginApi({ email, password });
  storeTokens(tokens.access_token, tokens.refresh_token);
  const user = await getCurrentUserApi();
  storeUser(user);
  return user;
}

export async function signUpAsync(payload: {
  email: string;
  name: string;
  password: string;
  role: Role;
  seller_ids?: string[];
  warehouse_ids?: string[];
  company_name?: string;
  seller_code?: string;
}): Promise<User> {
  return registerSellerPublicApi({
    email: payload.email,
    name: payload.name,
    password: payload.password,
    company_name: payload.company_name || payload.name,
    ...(payload.seller_code ? { seller_code: payload.seller_code } : {}),
  });
}

export async function signOutAsync(): Promise<void> {
  const refreshToken = readRefreshToken();
  try {
    if (refreshToken) {
      await logoutApi(refreshToken);
    }
  } finally {
    clearSession();
  }
}

export function signOut(): void {
  clearSession();
}

export function readUser(): User | null {
  return readStoredUser();
}

export function useAuth() {
  const [user, setUser] = useState<User | null>(() =>
    typeof window !== "undefined" ? readUser() : null,
  );
  const [ready, setReady] = useState(true);

  useEffect(() => {
    const sync = () => setUser(readUser());

    if (readUser()) {
      getCurrentUserApi()
        .then((serverUser) => {
          storeUser(serverUser);
          setUser(serverUser);
        })
        .catch((err: unknown) => {
          // Only clear session on explicit 401 Unauthorized error from server.
          // Never log out on history popstate, canceled requests, or transient network offline.
          const status = (err as { status?: number; code?: string })?.status;
          const code = (err as { status?: number; code?: string })?.code;
          if (status === 401 || code === "UNAUTHORIZED") {
            clearSession();
            setUser(null);
          }
        });
    }

    window.addEventListener("whitfield-auth", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("whitfield-auth", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  return { user, ready };
}

export const ROLE_SECTIONS: Record<Role, string[]> = {
  ADMINISTRATOR: [
    "/",
    "/inventory",
    "/receipts",
    "/orders",
    "/pick-tasks",
    "/shipments",
    "/transfers",
    "/returns",
    "/migration",
    "/admin",
    "/ai-assistant",
  ],
  WAREHOUSE_MANAGER: [
    "/",
    "/inventory",
    "/receipts",
    "/orders",
    "/pick-tasks",
    "/shipments",
    "/transfers",
    "/returns",
    "/migration",
    "/admin",
    "/ai-assistant",
  ],
  RECEIVER: ["/", "/receipts", "/inventory", "/returns", "/ai-assistant"],
  PICKER_PACKER: ["/", "/orders", "/pick-tasks", "/shipments", "/ai-assistant"],
  SELLER: ["/", "/inventory", "/orders", "/shipments", "/returns", "/ai-assistant"],
};
