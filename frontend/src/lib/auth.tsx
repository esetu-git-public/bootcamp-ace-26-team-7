import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { AuthUser } from "./api";

const STORAGE_KEY = "scd_auth";
const REMEMBER_EMAIL_KEY = "scd_remember_email";

export interface AuthState {
  user: AuthUser | null;
  token: string | null;
  isAuthenticated: boolean;
  isReady: boolean;
  signIn: (token: string, user: AuthUser) => void;
  signOut: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

function readStored(): { token: string; user: AuthUser } | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed?.token && parsed?.user) return parsed;
  } catch {
    // ignore
  }
  return null;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const stored = readStored();
    if (stored) {
      setToken(stored.token);
      setUser(stored.user);
    }
    setIsReady(true);
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      user,
      token,
      isAuthenticated: !!token,
      isReady,
      signIn: (t, u) => {
        setToken(t);
        setUser(u);
        if (typeof window !== "undefined") {
          window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ token: t, user: u }));
        }
      },
      signOut: () => {
        setToken(null);
        setUser(null);
        if (typeof window !== "undefined") {
          window.localStorage.removeItem(STORAGE_KEY);
        }
      },
    }),
    [user, token, isReady],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

export function getRememberedEmail(): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(REMEMBER_EMAIL_KEY) ?? "";
}

export function setRememberedEmail(email: string) {
  if (typeof window === "undefined") return;
  if (email) window.localStorage.setItem(REMEMBER_EMAIL_KEY, email);
  else window.localStorage.removeItem(REMEMBER_EMAIL_KEY);
}

// Local prediction history (per-user, in localStorage) — used until the
// backend exposes stats endpoints.
export interface HistoryEntry {
  id: string;
  createdAt: number;
  predicted_class: string;
  confidence: number;
  severity_label: "Low" | "Medium" | "High";
  severity_score: number;
  repair_cost_display: string;
  repair_time_display: string;
}

function historyKey(userId: string) {
  return `scd_history_${userId}`;
}

export function getHistory(userId: string): HistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(historyKey(userId));
    return raw ? (JSON.parse(raw) as HistoryEntry[]) : [];
  } catch {
    return [];
  }
}

export function addHistory(userId: string, entry: HistoryEntry) {
  if (typeof window === "undefined") return;
  const list = [entry, ...getHistory(userId)].slice(0, 50);
  window.localStorage.setItem(historyKey(userId), JSON.stringify(list));
}