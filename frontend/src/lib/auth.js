import React, { createContext, useContext, useEffect, useState } from "react";
import api from "@/lib/api";

const AuthCtx = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    const token = localStorage.getItem("d31337m3_token");
    if (!token) { setUser(null); setLoading(false); return; }
    try {
      const r = await api.get("/auth/me");
      setUser(r.data.user);
    } catch {
      localStorage.removeItem("d31337m3_token");
      setUser(null);
    } finally { setLoading(false); }
  };

  useEffect(() => { refresh(); }, []);

  const login = async (email, password) => {
    const r = await api.post("/auth/login", { email, password });
    localStorage.setItem("d31337m3_token", r.data.token);
    setUser(r.data.user);
    return r.data.user;
  };

  const register = async (email, password, name, promoCode) => {
    const r = await api.post("/auth/register", { email, password, name, promo_code: promoCode });
    localStorage.setItem("d31337m3_token", r.data.token);
    setUser(r.data.user);
    return r.data.user;
  };

  const logout = () => {
    localStorage.removeItem("d31337m3_token");
    setUser(null);
  };

  return <AuthCtx.Provider value={{ user, loading, login, register, logout, refresh }}>{children}</AuthCtx.Provider>;
};

export const useAuth = () => useContext(AuthCtx);
