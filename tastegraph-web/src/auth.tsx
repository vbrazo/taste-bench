import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { checkAuth, clearApiKey, getEndpoint, setApiKey, setEndpoint } from "./api";

export type AuthMode = "connected" | "local" | null;
const MODE_STORAGE = "tastegraph_mode";

interface AuthState {
  mode: AuthMode;
  endpoint: string;
  authed: boolean;
  connect: (endpoint: string, key: string) => Promise<void>;
  continueLocal: () => void;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

function loadMode(): AuthMode {
  try {
    return (localStorage.getItem(MODE_STORAGE) as AuthMode) || null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<AuthMode>(() => loadMode());
  const [endpoint, setEp] = useState<string>(() => getEndpoint());

  const connect = useCallback(async (ep: string, key: string) => {
    await checkAuth(ep, key); // throws on bad key / unreachable
    setEndpoint(ep);
    setApiKey(key);
    localStorage.setItem(MODE_STORAGE, "connected");
    setEp(ep.replace(/\/$/, ""));
    setMode("connected");
  }, []);

  const continueLocal = useCallback(() => {
    clearApiKey();
    localStorage.setItem(MODE_STORAGE, "local");
    setMode("local");
  }, []);

  const logout = useCallback(() => {
    clearApiKey();
    localStorage.removeItem(MODE_STORAGE);
    setMode(null);
  }, []);

  const value = useMemo<AuthState>(
    () => ({ mode, endpoint, authed: mode !== null, connect, continueLocal, logout }),
    [mode, endpoint, connect, continueLocal, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
