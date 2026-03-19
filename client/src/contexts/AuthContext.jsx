import { createContext, useContext, useMemo, useState } from "react";
import { authAPI } from "../api/authAPI";

const AuthContext = createContext(null);
const STORAGE_KEY = "lifequest.auth.session";

function getInitialSession() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      return {
        user: parsed?.user || null,
        token: parsed?.token || "",
      };
    }

    // Backward-compat: migrate older user-only auth state.
    const legacy = localStorage.getItem("lifequest.auth.user");
    if (legacy) {
      const legacyUser = JSON.parse(legacy);
      localStorage.removeItem("lifequest.auth.user");
      return { user: legacyUser || null, token: "" };
    }

    return { user: null, token: "" };
  } catch {
    return { user: null, token: "" };
  }
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(getInitialSession);

  const persistSession = (nextSession) => {
    setSession(nextSession);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(nextSession));
  };

  const register = async (payload) => {
    const result = await authAPI.register(payload);
    const nextSession = {
      user: result?.user || null,
      token: result?.access_token || "",
    };
    persistSession(nextSession);
    return result;
  };

  const login = async (payload) => {
    const result = await authAPI.login(payload);
    const nextSession = {
      user: result?.user || null,
      token: result?.access_token || "",
    };
    persistSession(nextSession);
    return result;
  };

  const logout = () => {
    setSession({ user: null, token: "" });
    localStorage.removeItem(STORAGE_KEY);
  };

  const value = useMemo(
    () => ({
      user: session.user,
      token: session.token,
      isAuthenticated: !!session.user && !!session.token,
      register,
      login,
      logout,
    }),
    [session],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
