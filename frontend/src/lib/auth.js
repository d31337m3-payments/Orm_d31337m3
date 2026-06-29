import React, { createContext, useContext, useEffect, useState } from "react";
import api from "@/lib/api";

const AuthCtx = createContext(null);

function getOrCreateDeviceId() {
  const key = "d31337m3_device_id";
  let id = localStorage.getItem(key);
  if (!id) {
    const raw = (typeof crypto !== "undefined" && crypto.randomUUID)
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    id = `web-${raw}`;
    localStorage.setItem(key, id);
  }
  return id;
}

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
    const r = await api.post("/auth/login", { email, password }, {
      headers: { "X-Device-Id": getOrCreateDeviceId() }
    });
    if (r.data?.requires_otp) {
      return {
        requiresOtp: true,
        challengeId: r.data.challenge_id,
        email,
        reason: r.data.reason,
      };
    }
    localStorage.setItem("d31337m3_token", r.data.token);
    setUser(r.data.user);
    return r.data.user;
  };

  const verifyLoginOtp = async (challengeId, email, otp, rememberDevice = true, deviceName = "") => {
    const r = await api.post("/auth/login/verify", {
      challenge_id: challengeId,
      email,
      otp,
      remember_device: rememberDevice,
      device_name: deviceName || undefined,
    }, {
      headers: { "X-Device-Id": getOrCreateDeviceId() }
    });
    localStorage.setItem("d31337m3_token", r.data.token);
    setUser(r.data.user);
    return r.data.user;
  };

  const resendLoginOtp = async (challengeId, email) => {
    const r = await api.post("/auth/login/resend", { challenge_id: challengeId, email });
    return {
      requiresOtp: true,
      challengeId: r.data.challenge_id,
      email,
      reason: r.data.reason,
    };
  };

  const register = async (email, password, name, promoCode) => {
    const r = await api.post("/auth/register", { email, password, name, promo_code: promoCode });
    if (r.data?.requires_verification) {
      return {
        requiresVerification: true,
        challengeId: r.data.challenge_id,
        email,
      };
    }
    if (r.data?.token) {
      localStorage.setItem("d31337m3_token", r.data.token);
      setUser(r.data.user);
      return r.data.user;
    }
    return r.data;
  };

  const verifyRegistrationOtp = async (challengeId, email, otp) => {
    const r = await api.post("/auth/register/verify", {
      challenge_id: challengeId,
      email,
      otp,
    });
    localStorage.setItem("d31337m3_token", r.data.token);
    setUser(r.data.user);
    return r.data.user;
  };

  const resendRegistrationOtp = async (challengeId, email) => {
    const r = await api.post("/auth/register/resend", { challenge_id: challengeId, email });
    return {
      requiresVerification: true,
      challengeId: r.data.challenge_id,
      email,
    };
  };

  const logout = () => {
    localStorage.removeItem("d31337m3_token");
    setUser(null);
  };

  return <AuthCtx.Provider value={{ user, loading, login, verifyLoginOtp, resendLoginOtp, register, verifyRegistrationOtp, resendRegistrationOtp, logout, refresh }}>{children}</AuthCtx.Provider>;
};

export const useAuth = () => useContext(AuthCtx);
