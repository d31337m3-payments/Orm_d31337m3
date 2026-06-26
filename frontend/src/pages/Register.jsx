import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Terminal } from "lucide-react";

export default function Register() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "", promo_code: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      await register(form.email, form.password, form.name, form.promo_code);
      nav("/billing");
    } catch (e) {
      setError(e.response?.data?.detail || "Registration failed");
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen bg-[#050505] flex items-center justify-center px-4">
      <div className="w-full max-w-md brutal-card p-10">
        <Link to="/" className="flex items-center gap-2 mb-8" data-testid="auth-logo">
          <Terminal className="text-[#FF3333]" size={20} />
          <span className="font-display font-black text-xl">d31337m3</span>
        </Link>
        <div className="overline mb-2">// new operator</div>
        <h1 className="font-display font-black text-3xl mb-8">Create account.</h1>
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
            {loading ? "Creating..." : "Create Account"}
          </button>
        </form>
        <div className="mt-6 text-center font-mono text-xs text-zinc-500">
          Have an account? <Link to="/login" data-testid="goto-login" className="text-white hover:text-[#FF3333]">sign in →</Link>
        </div>
      </div>
    </div>
  );
}
