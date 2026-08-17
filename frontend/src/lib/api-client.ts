import { clearSession, readAccessToken, readRefreshToken, storeTokens } from "./session";

export function getApiBaseUrl(): string {
  if (typeof window !== "undefined") {
    const custom = localStorage.getItem("wms_api_base_url");
    if (custom && custom.trim()) {
      const trimmed = custom.trim().replace(/\/+$/, "");
      return trimmed.endsWith("/api/v1") ? trimmed : `${trimmed}/api/v1`;
    }
    const injected = (window as unknown as Record<string, string>)["__WMS_API_URL__"];
    if (injected && injected.trim()) {
      const trimmed = injected.trim().replace(/\/+$/, "");
      return trimmed.endsWith("/api/v1") ? trimmed : `${trimmed}/api/v1`;
    }
  }
  const envMap = import.meta.env as unknown as Record<string, string>;
  const raw = envMap["VITE_API_BASE_URL"] || "http://127.0.0.1:8080";
  const trimmed = String(raw).trim().replace(/\/+$/, "");
  return trimmed.endsWith("/api/v1") ? trimmed : `${trimmed}/api/v1`;
}

export function setCustomApiBaseUrl(url: string): void {
  if (typeof window !== "undefined") {
    if (url.trim()) {
      localStorage.setItem("wms_api_base_url", url.trim());
    } else {
      localStorage.removeItem("wms_api_base_url");
    }
  }
}

export const API_BASE_URL = getApiBaseUrl();

export interface ApiErrorResponse {
  error?: {
    code?: string;
    message?: string;
    details?: Record<string, unknown>;
    request_id?: string;
  };
  detail?: string | Array<{ msg: string; loc: string[] }>;
}

export class ApiError extends Error {
  status: number;
  code?: string;
  details?: unknown;

  constructor(message: string, status: number, code?: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    if (code !== undefined) {
      this.code = code;
    }
    this.details = details;
  }
}

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = readRefreshToken();
  if (!refreshToken) return null;

  const base = getApiBaseUrl();
  const response = await fetch(`${base}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    clearSession();
    return null;
  }

  const body = (await response.json()) as {
    access_token: string;
    refresh_token?: string;
  };
  storeTokens(body.access_token, body.refresh_token);
  return body.access_token;
}

async function parseError(response: Response): Promise<ApiError> {
  let errorBody: ApiErrorResponse | null = null;
  try {
    errorBody = await response.json();
  } catch {
    // Non-JSON errors are normalized below.
  }

  const message =
    errorBody?.error?.message ||
    (typeof errorBody?.detail === "string"
      ? errorBody.detail
      : Array.isArray(errorBody?.detail)
        ? errorBody.detail.map((d) => d.msg).join(", ")
        : `Request failed with status ${response.status}`);

  return new ApiError(message, response.status, errorBody?.error?.code, errorBody?.error?.details);
}

async function requestWithToken(endpoint: string, options: RequestInit, token: string | null) {
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  const headers: Record<string, string> = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const base = getApiBaseUrl();
  const url = endpoint.startsWith("http") ? endpoint : `${base}${endpoint}`;
  return fetch(url, {
    ...options,
    headers,
  });
}

function shouldRefreshAfterUnauthorized(endpoint: string): boolean {
  if (endpoint.startsWith("http")) return true;
  return !["/auth/login", "/auth/register-seller", "/auth/refresh"].includes(endpoint);
}

export async function apiRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  try {
    let response = await requestWithToken(endpoint, options, readAccessToken());

    if (response.status === 401 && shouldRefreshAfterUnauthorized(endpoint)) {
      const refreshedToken = await refreshAccessToken();
      if (refreshedToken) {
        response = await requestWithToken(endpoint, options, refreshedToken);
      }
      if (response.status === 401) {
        clearSession();
        throw new ApiError("Session expired. Please log in again.", 401, "UNAUTHORIZED");
      }
    }

    if (!response.ok) {
      throw await parseError(response);
    }

    if (response.status === 204) {
      return {} as T;
    }

    const data = await response.json();
    return data as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    const isFetchFail = error instanceof Error && error.message === "Failed to fetch";
    const message = isFetchFail
      ? `Cannot connect to API at ${getApiBaseUrl()}. Ensure your Render backend is running and CORS is allowed.`
      : error instanceof Error
        ? error.message
        : "Network error occurred";
    throw new ApiError(message, 0, "NETWORK_ERROR");
  }
}
