import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import SupportChatWidget from "@/components/SupportChatWidget";
import { Terminal } from "lucide-react";

export default function Login() {
  const { login, verifyLoginOtp, resendLoginOtp } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [challenge, setChallenge] = useState(null);
  const [otp, setOtp] = useState("");
  const [rememberDevice, setRememberDevice] = useState(true);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [resendMsg, setResendMsg] = useState("");

  const onSubmit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const result = await login(email, password);
      if (result?.requiresOtp) {
        setChallenge(result);
      } else {
        nav(result.is_admin ? "/admin" : "/dashboard");
      }
    } catch (e) {
      setError(e.response?.data?.detail || "Login failed");
    } finally { setLoading(false); }
  };

  const onVerifyOtp = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const u = await verifyLoginOtp(challenge.challengeId, challenge.email, otp.trim(), rememberDevice, "Web Browser");
      nav(u.is_admin ? "/admin" : "/dashboard");
    } catch (e) {
      setError(e.response?.data?.detail || "OTP verification failed");
    } finally { setLoading(false); }
  };

  const onResendOtp = async () => {
    if (!challenge) return;
    setError("");
    setResendMsg("");
    setResending(true);
    try {
      const next = await resendLoginOtp(challenge.challengeId, challenge.email);
      setChallenge(next);
      setResendMsg("A new verification code has been sent.");
    } catch (e) {
      setError(e.response?.data?.detail || "Could not resend OTP");
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#050505] flex items-center justify-center px-4">
      <div className="w-full max-w-md brutal-card p-10">
        <Link to="/" className="flex items-center gap-2 mb-8" data-testid="auth-logo">
          <Terminal className="text-[#FF3333]" size={20} />
          <span className="font-display font-black text-xl">d31337m3</span>
        </Link>
        <div className="overline mb-2">// authenticate</div>
        <h1 className="font-display font-black text-3xl mb-8">{challenge ? "Verify login." : "Sign in."}</h1>
        {!challenge ? (
          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <div className="overline mb-1">email</div>
              <input data-testid="login-email" type="email" required value={email} onChange={(e)=>setEmail(e.target.value)} className="brutal-input" />
            </div>
            <div>
              <div className="overline mb-1">password</div>
              <input data-testid="login-password" type="password" required value={password} onChange={(e)=>setPassword(e.target.value)} className="brutal-input" />
            </div>
            {error && <div data-testid="login-error" className="font-mono text-xs text-[#FF3333] py-2">› {error}</div>}
            <button data-testid="login-submit" type="submit" disabled={loading} className="brutal-btn brutal-btn-primary w-full">
              {loading ? "Authenticating..." : "Sign In"}
            </button>
          </form>
        ) : (
          <form onSubmit={onVerifyOtp} className="space-y-4">
            <p className="font-mono text-xs text-zinc-400">
              Enter the 6-digit code sent to <span className="text-white">{challenge.email}</span>.
            </p>
            <div>
              <div className="overline mb-1">otp code</div>
              <input
                data-testid="login-otp"
                type="text"
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                required
                value={otp}
                onChange={(e)=>setOtp(e.target.value.replace(/\D/g, ""))}
                className="brutal-input"
                placeholder="123456"
              />
            </div>
            <label className="flex items-center gap-2 font-mono text-xs text-zinc-300">
              <input
                data-testid="login-remember-device"
                type="checkbox"
                checked={rememberDevice}
                onChange={(e)=>setRememberDevice(e.target.checked)}
              />
              Remember this device
            </label>
            {error && <div data-testid="login-error" className="font-mono text-xs text-[#FF3333] py-2">› {error}</div>}
            {resendMsg && <div className="font-mono text-xs text-[#00FF41] py-2">› {resendMsg}</div>}
            <button data-testid="login-verify-submit" type="submit" disabled={loading} className="brutal-btn brutal-btn-primary w-full">
              {loading ? "Verifying..." : "Verify & Sign In"}
            </button>
            <button data-testid="login-resend-submit" type="button" disabled={resending} onClick={onResendOtp} className="brutal-btn w-full">
              {resending ? "Resending..." : "Resend Code"}
            </button>
          </form>
        )}
        <div className="mt-6 text-center font-mono text-xs text-zinc-500">
          New here? <Link to="/register" data-testid="goto-register" className="text-white hover:text-[#FF3333]">create an account →</Link>
        </div>
        <div className="mt-4 border-t border-[#222] pt-4 font-mono text-xs text-zinc-400" data-testid="login-support-links">
          Locked out?
          <span className="text-zinc-500"> Use the </span>
          <span className="text-white">anonymous customer support chat (email OTP verified)</span>
          <span className="text-zinc-500"> button in the bottom-right, or email </span>
          <a className="text-white hover:text-[#FF3333]" href="mailto:support@d31337m3.com">support@d31337m3.com</a>
          <span className="text-zinc-500">.</span>
        </div>
      </div>
      <SupportChatWidget allowAnonymous />
    </div>
  );
}
