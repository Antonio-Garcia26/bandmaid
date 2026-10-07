"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { mutateJson, requestJson, type SessionResponse } from "@/lib/api-client";
import type { FanUser } from "@/lib/types";

type AuthContextValue = {
  user: FanUser | null;
  configured: boolean | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  acceptUser: (user: FanUser) => void;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<FanUser | null>(null);
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const session = await requestJson<SessionResponse>("/api/auth/session");
      setUser(session.user);
      setConfigured(session.configured);
    } catch {
      setError("No se pudo comprobar la sesión. Inténtalo de nuevo.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    requestJson<SessionResponse>("/api/auth/session")
      .then((session) => {
        if (cancelled) return;
        setUser(session.user);
        setConfigured(session.configured);
      })
      .catch(() => {
        if (!cancelled) setError("No se pudo comprobar la sesión. Inténtalo de nuevo.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const acceptUser = useCallback((nextUser: FanUser) => {
    setUser(nextUser);
    setConfigured(true);
    setError(null);
  }, []);

  const signOut = useCallback(async () => {
    await mutateJson<{ ok: boolean }>("/api/auth/logout", {});
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, configured, loading, error, refresh, acceptUser, signOut }),
    [user, configured, loading, error, refresh, acceptUser, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth debe usarse dentro de AuthProvider.");
  return context;
}
