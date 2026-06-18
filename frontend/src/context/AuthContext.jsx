import React, { createContext, useContext, useEffect, useState, useMemo, useCallback } from "react";
import api from "../lib/api";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null = checking, false = anon, obj = authed
  const [loading, setLoading] = useState(true);

  // Mount-only: check existing session. Intentionally runs once.
  useEffect(() => {
    api.get("/auth/me")
      .then((r) => setUser(r.data))
      .catch(() => setUser(false))
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    setUser(data);
    return data;
  }, []);

  const register = useCallback(async (email, password, name) => {
    const { data } = await api.post("/auth/register", { email, password, name });
    setUser(data);
    return data;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } catch (err) {
      if (process.env.NODE_ENV !== "production") console.error("Logout request failed:", err);
    }
    setUser(false);
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const r = await api.get("/auth/me");
      setUser(r.data);
      return r.data;
    } catch (err) {
      if (process.env.NODE_ENV !== "production") console.error("refreshUser failed:", err);
      return undefined;
    }
  }, []);

  const value = useMemo(
    () => ({ user, setUser, loading, login, register, logout, refreshUser }),
    [user, loading, login, register, logout, refreshUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
