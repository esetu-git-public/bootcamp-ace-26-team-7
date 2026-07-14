// Typed API client for the Surface Crack Detection FastAPI backend.
// Base URL is configured via VITE_API_BASE_URL. If empty, same-origin.

export const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
}

export interface AuthSuccess {
  success: true;
  access_token: string;
  user: AuthUser;
}

export interface RegisterSuccess {
  success: true;
  message: string;
  user: AuthUser;
}

export interface MessageSuccess {
  success: true;
  message: string;
}

export type DefectClass = "Cracks" | "Patch" | "Potholes" | "Surface Defects";
export type SeverityLabel = "Low" | "Medium" | "High";

export interface PredictionResult {
  success: true;
  predicted_class: DefectClass;
  confidence: number;
  class_probabilities: Record<DefectClass, number>;
  severity_score: number;
  severity_label: SeverityLabel;
  repair_cost: { low: number; high: number; display: string; currency: string };
  repair_time: { low: number; high: number; display: string; unit: string };
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

type FetchOpts = {
  method?: string;
  body?: unknown;
  token?: string | null;
  formData?: FormData;
};

async function apiFetch<T>(path: string, opts: FetchOpts = {}): Promise<T> {
  if (!API_BASE && typeof window !== "undefined") {
    // Give a clear runtime error rather than a confusing same-origin 404.
    // Keep going — allows same-origin deployment when the API is proxied.
  }
  const headers: Record<string, string> = {};
  if (opts.token) headers["Authorization"] = `Bearer ${opts.token}`;

  let body: BodyInit | undefined;
  if (opts.formData) {
    body = opts.formData;
  } else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: opts.method ?? (body ? "POST" : "GET"),
      headers,
      body,
    });
  } catch (e) {
    throw new ApiError(0, e instanceof Error ? e.message : "Network error");
  }

  const text = await res.text();
  let json: unknown = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    // non-JSON response
  }

  if (!res.ok) {
    const message =
      (json && typeof json === "object" && "message" in json && typeof (json as { message: unknown }).message === "string"
        ? (json as { message: string }).message
        : null) ??
      (json && typeof json === "object" && "detail" in json
        ? String((json as { detail: unknown }).detail)
        : null) ??
      res.statusText ??
      "Request failed";
    throw new ApiError(res.status, message);
  }

  return json as T;
}

export const api = {
  login: (email: string, password: string) =>
    apiFetch<AuthSuccess>("/api/auth/login", { body: { email, password } }),

  register: (email: string, password: string, full_name: string) =>
    apiFetch<RegisterSuccess>("/api/auth/register", {
      body: { email, password, full_name },
    }),

  forgotPassword: (email: string) =>
    apiFetch<MessageSuccess>("/api/auth/forgot-password", { body: { email } }),

  githubStart: (redirectTo: string) =>
    apiFetch<{ url: string }>(
      `/api/auth/github?redirect_to=${encodeURIComponent(redirectTo)}`,
    ),

  githubCallback: (code: string) =>
    apiFetch<AuthSuccess>(
      `/api/auth/github/callback?code=${encodeURIComponent(code)}`,
    ),

  predict: (file: File, token: string) => {
    const fd = new FormData();
    fd.append("image", file);
    return apiFetch<PredictionResult>("/api/predict", {
      method: "POST",
      formData: fd,
      token,
    });
  },
};