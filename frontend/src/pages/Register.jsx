import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import SupportChatWidget from "@/components/SupportChatWidget";
import { Terminal } from "lucide-react";

export default function Register() {
  const { register, verifyRegistrationOtp, resendRegistrationOtp } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "", promo_code: "" });
  const [challenge, setChallenge] = useState(null);
  const [otp, setOtp] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [resendMsg, setResendMsg] = useState("");

  const onSubmit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const result = await register(form.email, form.password, form.name, form.promo_code);
      if (result?.requiresVerification) {
        setChallenge(result);
      } else {
        nav("/billing");
      }
    } catch (e) {
      setError(e.response?.data?.detail || "Registration failed");
    } finally { setLoading(false); }
  };

  const onVerifyOtp = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      await verifyRegistrationOtp(challenge.challengeId, challenge.email, otp.trim());
      nav("/billing");
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
      const next = await resendRegistrationOtp(challenge.challengeId, challenge.email);
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
        <div className="overline mb-2">// new operator</div>
        <h1 className="font-display font-black text-3xl mb-8">{challenge ? "Verify email." : "Create account."}</h1>
        {!challenge ? (
          <form onSubmit={onSubmit} className="space-y-4">
            <div><div className="overline mb-1">name</div>
              <input data-testid="register-name" required value={form.name} onChange={(e)=>setForm({...form,name:e.target.value})} className="brutal-input" /></div>
            <div><div className="overline mb-1">email</div>
              <input data-testid="register-email" type="email" required value={form.email} onChange={(e)=>setForm({...form,email:e.target.value})} className="brutal-input" /></div>
            <div><div className="overline mb-1">password (6+ chars)</div>
              <input data-testid="register-password" type="password" required minLength={6} value={form.password} onChange={(e)=>setForm({...form,password:e.target.value})} className="brutal-input" /></div>
            <div><div className="overline mb-1">promo code (optional)</div>
              <input data-testid="register-promo-code" type="text" value={form.promo_code} onChange={(e)=>setForm({...form,promo_code:e.target.value})} className="brutal-input" placeholder="OCanada75" /></div>
            {error && <div data-testid="register-error" className="font-mono text-xs text-[#FF3333] py-2">› {error}</div>}
            <button data-testid="register-submit" type="submit" disabled={loading} className="brutal-btn brutal-btn-primary w-full">
              {loading ? "Sending code..." : "Create Account"}
            </button>
          </form>
        ) : (
          <form onSubmit={onVerifyOtp} className="space-y-4">
            <p className="font-mono text-xs text-zinc-400">
              We sent a 6-digit verification code to <span className="text-white">{challenge.email}</span>.
            </p>
            <div><div className="overline mb-1">email verification code</div>
              <input
                data-testid="register-otp"
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
            {error && <div data-testid="register-error" className="font-mono text-xs text-[#FF3333] py-2">› {error}</div>}
            {resendMsg && <div className="font-mono text-xs text-[#00FF41] py-2">› {resendMsg}</div>}
            <button data-testid="register-verify-submit" type="submit" disabled={loading} className="brutal-btn brutal-btn-primary w-full">
              {loading ? "Verifying..." : "Verify & Continue"}
            </button>
            <button data-testid="register-resend-submit" type="button" disabled={resending} onClick={onResendOtp} className="brutal-btn w-full">
              {resending ? "Resending..." : "Resend Code"}
            </button>
          </form>
        )}
        <div className="mt-6 text-center font-mono text-xs text-zinc-500">
          Have an account? <Link to="/login" data-testid="goto-login" className="text-white hover:text-[#FF3333]">sign in →</Link>
        </div>
        <div className="mt-4 border-t border-[#222] pt-4 font-mono text-xs text-zinc-400" data-testid="register-support-links">
          Need help before logging in?
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
