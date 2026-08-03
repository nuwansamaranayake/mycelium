/* SHELL: vendored from groundwork/webshell — edit there, not here. */
import { useCallback, useEffect, useState } from "react";

export function useDemoSession<S extends { token: string }>(storageKey: string) {
  const [session, setSession] = useState<S | null>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const raw = sessionStorage.getItem(storageKey);
    if (raw) try { setSession(JSON.parse(raw)); } catch { /* stale */ }
  }, [storageKey]);
  const start = useCallback(async () => {
    setBusy(true); setErr("");
    try {
      const r = await fetch("/api/v1/demo/session", { method: "POST" });
      if (!r.ok) { setErr(`could not open a session: HTTP ${r.status} — ${(await r.json()).detail ?? ""}`); return; }
      const s = (await r.json()) as S;
      sessionStorage.setItem(storageKey, JSON.stringify(s));
      setSession(s);
    } catch (e) { setErr(`could not reach the API: ${String(e)}`); }
    finally { setBusy(false); }
  }, [storageKey]);
  const drop = useCallback(() => { sessionStorage.removeItem(storageKey); setSession(null); }, [storageKey]);
  return { session, start, drop, err, busy };
}

export async function api<T>(token: string, path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...(init?.headers ?? {}) },
  });
  if (r.status === 401) throw new Error("SESSION_EXPIRED");
  if (r.status === 429) throw new Error("BUDGET_EXHAUSTED");
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    const err = new Error(`HTTP ${r.status}`) as Error & { detail?: unknown };
    err.detail = body?.detail;
    throw err;
  }
  return r.json();
}

export function friendly(e: unknown): string {
  const m = e instanceof Error ? e.message : String(e);
  if (m === "SESSION_EXPIRED")
    return "This demo session expired. Start a new one. Seeded data was synthetic; anything you uploaded stays in its expired tenant until the retention sweep deletes it.";
  if (m === "BUDGET_EXHAUSTED") return "This session's request budget is spent. Start a new one.";
  return m;
}
