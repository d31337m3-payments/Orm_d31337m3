import React from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import CanadaFlag from "@/components/CanadaFlag";
import { LayoutDashboard, KeyRound, Search, CreditCard, ShieldAlert, LogOut, Terminal, FileText } from "lucide-react";

const NavLink = ({ to, icon: Icon, label, testid }) => {
  const loc = useLocation();
  const active = loc.pathname === to;
  return (
    <Link
      to={to}
      data-testid={testid}
      className={`flex items-center gap-3 px-4 py-3 border-l-2 transition-all text-sm font-mono uppercase tracking-wider ${
        active ? "border-[#FF3333] bg-[#111] text-white" : "border-transparent text-zinc-500 hover:text-white hover:bg-[#0a0a0a]"
      }`}
    >
      <Icon size={16} /> {label}
    </Link>
  );
};

export default function DashboardLayout({ children, title }) {
  const { user, logout } = useAuth();
  const nav = useNavigate();

  return (
    <div className="min-h-screen flex bg-[#050505]">
      {/* Sidebar */}
      <aside className="w-64 border-r border-[#222] bg-black flex flex-col" data-testid="sidebar">
        <Link to="/" className="px-6 py-6 border-b border-[#222] flex items-center gap-2">
          <Terminal className="text-[#FF3333]" size={20} />
          <span className="font-display font-black text-xl tracking-tighter">d31337m3</span>
        </Link>
        <nav className="flex-1 py-4">
          <NavLink to="/dashboard" icon={LayoutDashboard} label="Overview" testid="nav-dashboard" />
          <NavLink to="/keywords" icon={KeyRound} label="Keywords" testid="nav-keywords" />
          <NavLink to="/findings" icon={Search} label="Findings" testid="nav-findings" />
          <NavLink to="/documents" icon={FileText} label="Documents" testid="nav-documents" />
          <NavLink to="/billing" icon={CreditCard} label="Billing" testid="nav-billing" />
          {user?.is_admin && <NavLink to="/admin" icon={ShieldAlert} label="Admin" testid="nav-admin" />}
        </nav>
        <div className="border-t border-[#222] p-4">
          <div className="text-xs font-mono text-zinc-500 mb-2 truncate" data-testid="sidebar-user-email">{user?.email}</div>
          <div className="text-xs font-mono text-zinc-600 mb-3">PLAN: <span className="text-white">{(user?.plan_id || "trial").toUpperCase()}</span></div>
          <button onClick={() => { logout(); nav("/"); }} data-testid="logout-button" className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-zinc-500 hover:text-[#FF3333]">
            <LogOut size={14} /> Logout
          </button>
          <div className="mt-4 pt-3 border-t border-[#222] flex items-center gap-2 text-xs font-mono text-zinc-600">
            <CanadaFlag size={12} /> Made in Canada
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 flex flex-col">
        <header className="border-b border-[#222] px-8 py-5 flex items-center justify-between">
          <div>
            <div className="overline mb-1">d31337m3 // control</div>
            <h1 className="font-display font-bold text-2xl tracking-tight" data-testid="page-title">{title}</h1>
          </div>
          <div className="font-mono text-xs text-zinc-500 flex items-center gap-3">
            <CanadaFlag size={14} />
            {new Date().toISOString().slice(0,19)}Z
          </div>
        </header>
        <div className="flex-1 p-8 bg-[#0a0a0a]">{children}</div>
      </main>
    </div>
  );
}
