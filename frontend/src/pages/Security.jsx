import React, { useEffect, useState } from "react";
import DashboardLayout from "@/components/DashboardLayout";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function Security() {
  const { user } = useAuth();
  const [status, setStatus] = useState({ enabled: false, method: "email", email_verified: true });
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const [passwordForEnable, setPasswordForEnable] = useState("");
  const [passwordForDisable, setPasswordForDisable] = useState("");
  const [challenge, setChallenge] = useState(null);
  const [otp, setOtp] = useState("");

  const load = async () => {
    const [s, d] = await Promise.all([api.get("/auth/2fa"), api.get("/auth/devices")]);
    setStatus(s.data || { enabled: false, method: "email", email_verified: true });
    setDevices(d.data?.devices || []);
  };

  useEffect(() => {
    load().catch(() => {});
  }, []);

  const startEnable = async (e) => {
    e.preventDefault();
    setLoading(true); setError(""); setMessage("");
    try {
      const r = await api.post("/auth/2fa/enable/start", { password: passwordForEnable });
      setChallenge(r.data);
      setMessage("Verification code sent to your email.");
      setPasswordForEnable("");
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to start 2FA enable flow.");
    } finally {
      setLoading(false);
    }
  };

  const verifyEnable = async (e) => {
    e.preventDefault();
    if (!challenge) return;
    setLoading(true); setError(""); setMessage("");
    try {
      await api.post("/auth/2fa/enable/verify", {
        challenge_id: challenge.challenge_id,
        email: user?.email,
        otp: otp.trim(),
      });
      setChallenge(null);
      setOtp("");
      setMessage("2FA enabled successfully.");
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || "Invalid code.");
    } finally {
      setLoading(false);
    }
  };

  const disable2fa = async (e) => {
    e.preventDefault();
    setLoading(true); setError(""); setMessage("");
    try {
      await api.post("/auth/2fa/disable", { password: passwordForDisable });
      setPasswordForDisable("");
      setChallenge(null);
      setOtp("");
      setMessage("2FA disabled.");
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to disable 2FA.");
    } finally {
      setLoading(false);
    }
  };

  const revokeDevice = async (id) => {
    setLoading(true); setError(""); setMessage("");
    try {
      await api.delete(`/auth/devices/${id}`);
      setMessage("Device revoked.");
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to revoke device.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <DashboardLayout title="Security Settings">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="brutal-card p-6" data-testid="security-twofa-panel">
          <div className="overline mb-2">// account security</div>
          <h2 className="font-display font-black text-2xl mb-4">Two-Factor Authentication</h2>
          <div className="font-mono text-xs text-zinc-400 mb-4">
            Email verified: <span className="text-white">{status.email_verified ? "YES" : "NO"}</span>
            <br />
            2FA status: <span className="text-white">{status.enabled ? "ENABLED" : "DISABLED"}</span>
          </div>

          {!status.enabled ? (
            <>
              {!challenge ? (
                <form onSubmit={startEnable} className="space-y-3">
                  <div>
                    <div className="overline mb-1">confirm password</div>
                    <input
                      data-testid="security-enable-password"
                      type="password"
                      required
                      value={passwordForEnable}
                      onChange={(e) => setPasswordForEnable(e.target.value)}
                      className="brutal-input"
                    />
                  </div>
                  <button data-testid="security-enable-2fa" type="submit" disabled={loading} className="brutal-btn brutal-btn-primary w-full">
                    {loading ? "Sending code..." : "Enable 2FA"}
                  </button>
                </form>
              ) : (
                <form onSubmit={verifyEnable} className="space-y-3">
                  <div className="font-mono text-xs text-zinc-400">
                    Enter the verification code sent to <span className="text-white">{user?.email}</span>.
                  </div>
                  <div>
                    <div className="overline mb-1">otp code</div>
                    <input
                      data-testid="security-enable-otp"
                      type="text"
                      inputMode="numeric"
                      pattern="[0-9]{6}"
                      maxLength={6}
                      required
                      value={otp}
                      onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
                      className="brutal-input"
                    />
                  </div>
                  <button data-testid="security-verify-enable" type="submit" disabled={loading} className="brutal-btn brutal-btn-primary w-full">
                    {loading ? "Verifying..." : "Verify & Enable"}
                  </button>
                </form>
              )}
            </>
          ) : (
            <form onSubmit={disable2fa} className="space-y-3">
              <div>
                <div className="overline mb-1">confirm password</div>
                <input
                  data-testid="security-disable-password"
                  type="password"
                  required
                  value={passwordForDisable}
                  onChange={(e) => setPasswordForDisable(e.target.value)}
                  className="brutal-input"
                />
              </div>
              <button data-testid="security-disable-2fa" type="submit" disabled={loading} className="brutal-btn w-full">
                {loading ? "Disabling..." : "Disable 2FA"}
              </button>
            </form>
          )}

          {message && <div className="mt-3 font-mono text-xs text-[#00FF41]">› {message}</div>}
          {error && <div className="mt-3 font-mono text-xs text-[#FF3333]">› {error}</div>}
        </div>

        <div className="brutal-card p-6" data-testid="security-devices-panel">
          <div className="overline mb-2">// recognized devices</div>
          <h2 className="font-display font-black text-2xl mb-4">Trusted Devices</h2>
          {devices.length === 0 ? (
            <div className="font-mono text-sm text-zinc-500">No trusted devices yet.</div>
          ) : (
            <div className="space-y-3">
              {devices.map((d) => (
                <div key={d.id} className="border border-[#222] p-3 rounded">
                  <div className="font-mono text-xs text-zinc-400">{d.device_name || "Unknown Device"}</div>
                  <div className="font-mono text-[11px] text-zinc-500 mt-1">Trusted until: {d.trusted_until?.slice(0, 19) || "-"}</div>
                  <div className="font-mono text-[11px] text-zinc-500">Last seen: {d.last_seen_at?.slice(0, 19) || "-"}</div>
                  <button
                    data-testid={`security-revoke-device-${d.id}`}
                    onClick={() => revokeDevice(d.id)}
                    disabled={loading}
                    className="mt-2 brutal-btn !py-1 !px-3"
                    type="button"
                  >
                    Revoke
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
