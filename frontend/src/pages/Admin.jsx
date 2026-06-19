import React, { useEffect, useState } from "react";
import DashboardLayout from "@/components/DashboardLayout";
import api from "@/lib/api";

const Stat = ({ label, value, testid }) => (
  <div className="brutal-card p-5" data-testid={testid}>
    <div className="overline mb-2">{label}</div>
    <div className="font-display font-black text-3xl">{value}</div>
  </div>
);

export default function Admin() {
  const [stats, setStats] = useState(null);
  const [tab, setTab] = useState("payments");
  const [users, setUsers] = useState([]);
  const [payments, setPayments] = useState([]);
  const [emails, setEmails] = useState([]);
  const [removals, setRemovals] = useState([]);

  const load = async () => {
    const [s, u, p, e, r] = await Promise.all([
      api.get("/admin/stats"),
      api.get("/admin/users"),
      api.get("/admin/payments"),
      api.get("/admin/email-log"),
      api.get("/admin/removals"),
    ]);
    setStats(s.data); setUsers(u.data.users); setPayments(p.data.payments); setEmails(e.data.emails); setRemovals(r.data.removals);
  };
  useEffect(() => { load(); }, []);

  const confirm = async (id) => { await api.post(`/admin/payments/${id}/confirm`); load(); };
  const reject = async (id) => { await api.post(`/admin/payments/${id}/reject`); load(); };
  const markRemoved = async (id) => { await api.post(`/admin/removals/${id}/mark-removed`); load(); };

  if (!stats) return <DashboardLayout title="Admin"><div className="font-mono">loading<span className="blink">_</span></div></DashboardLayout>;

  return (
    <DashboardLayout title="Admin Console">
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-6">
        <Stat label="Users" value={stats.users} testid="admin-stat-users" />
        <Stat label="Active Subs" value={stats.active_subs} testid="admin-stat-subs" />
        <Stat label="Keywords" value={stats.keywords} testid="admin-stat-keywords" />
        <Stat label="Findings" value={stats.findings_total} testid="admin-stat-findings" />
        <Stat label="Active" value={stats.findings_active} testid="admin-stat-findings-active" />
        <Stat label="Pending Pays" value={stats.pending_payments} testid="admin-stat-pending-payments" />
        <Stat label="Removals" value={stats.removal_requests} testid="admin-stat-removals" />
      </div>

      <div className="flex gap-2 mb-4" data-testid="admin-tabs">
        {[["payments","Payments"],["removals","Removals"],["users","Users"],["emails","Email Log"]].map(([k,l]) => (
          <button key={k} onClick={()=>setTab(k)} data-testid={`admin-tab-${k}`}
            className={`font-mono text-xs px-4 py-2 border ${tab===k ? "border-white text-white" : "border-[#222] text-zinc-500 hover:text-white"}`}>
            {l.toUpperCase()}
          </button>
        ))}
      </div>

      {tab === "payments" && (
        <div className="brutal-card p-6">
          <table className="w-full" data-testid="admin-payments-table">
            <thead><tr className="border-b border-[#222]">{["User","Plan","Method","Amount","Status","TX","Date","Action"].map(h=><th key={h} className="overline text-left py-2">{h}</th>)}</tr></thead>
            <tbody>
              {payments.map(p => (
                <tr key={p.id} className="border-b border-[#222]">
                  <td className="py-3 font-mono text-xs">{users.find(u=>u.id===p.user_id)?.email || p.user_id?.slice(0,8)}</td>
                  <td className="py-3 font-mono text-sm">{p.plan_id}</td>
                  <td className="py-3 font-mono text-xs">{p.method}</td>
                  <td className="py-3 font-mono text-sm">${p.amount_usd}</td>
                  <td className="py-3 font-mono text-xs">{p.status}</td>
                  <td className="py-3 font-mono text-xs text-zinc-500 truncate max-w-[120px]">{p.tx_hash?.slice(0,16) || "—"}</td>
                  <td className="py-3 font-mono text-xs text-zinc-500">{p.created_at?.slice(0,10)}</td>
                  <td className="py-3 flex gap-2">
                    {p.status !== "confirmed" && p.status !== "rejected" && (
                      <>
                        <button onClick={()=>confirm(p.id)} data-testid={`confirm-payment-${p.id}`} className="font-mono text-xs text-[#00FF41] hover:text-white">CONFIRM</button>
                        <button onClick={()=>reject(p.id)} data-testid={`reject-payment-${p.id}`} className="font-mono text-xs text-[#FF3333] hover:text-white">REJECT</button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "users" && (
        <div className="brutal-card p-6">
          <table className="w-full" data-testid="admin-users-table">
            <thead><tr className="border-b border-[#222]">{["Email","Name","Provider","Plan","Status","Admin","Created"].map(h=><th key={h} className="overline text-left py-2">{h}</th>)}</tr></thead>
            <tbody>
              {users.map(u => (
                <tr key={u.id} className="border-b border-[#222]">
                  <td className="py-3 font-mono text-sm">{u.email}</td>
                  <td className="py-3 font-mono text-xs">{u.name}</td>
                  <td className="py-3 font-mono text-xs">{u.auth_provider}</td>
                  <td className="py-3 font-mono text-xs">{u.plan_id || "—"}</td>
                  <td className="py-3 font-mono text-xs">{u.subscription_status}</td>
                  <td className="py-3 font-mono text-xs">{u.is_admin ? "YES" : "—"}</td>
                  <td className="py-3 font-mono text-xs text-zinc-500">{u.created_at?.slice(0,10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "emails" && (
        <div className="brutal-card p-6">
          <table className="w-full" data-testid="admin-emails-table">
            <thead><tr className="border-b border-[#222]">{["Sent","To","Subject","Status"].map(h=><th key={h} className="overline text-left py-2">{h}</th>)}</tr></thead>
            <tbody>
              {emails.map(e => (
                <tr key={e.id} className="border-b border-[#222]">
                  <td className="py-3 font-mono text-xs text-zinc-500">{e.sent_at?.slice(0,16)}</td>
                  <td className="py-3 font-mono text-xs">{e.to}</td>
                  <td className="py-3 font-mono text-sm">{e.subject}</td>
                  <td className="py-3 font-mono text-xs">{e.mocked ? "MOCKED" : e.delivered ? "SENT" : "FAILED"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "removals" && (
        <div className="brutal-card p-6">
          <table className="w-full" data-testid="admin-removals-table">
            <thead><tr className="border-b border-[#222]">{["Created","User","Broker","Dispatched To","Status","Action"].map(h=><th key={h} className="overline text-left py-2">{h}</th>)}</tr></thead>
            <tbody>
              {removals.length === 0 ? (
                <tr><td colSpan={6} className="py-6 font-mono text-zinc-500">No removal requests yet.</td></tr>
              ) : removals.map(r => (
                <tr key={r.id} className="border-b border-[#222]">
                  <td className="py-3 font-mono text-xs text-zinc-500">{r.created_at?.slice(0,16)}</td>
                  <td className="py-3 font-mono text-xs">{r.user_email}</td>
                  <td className="py-3 font-mono text-sm">{r.broker}</td>
                  <td className="py-3 font-mono text-xs text-zinc-400">{r.broker_email || "—"}</td>
                  <td className="py-3 font-mono text-xs">
                    {r.status === "removed" ? <span className="text-[#00FF41]">REMOVED</span>
                      : r.status === "dispatched" ? <span className="text-[#FFD700]">DISPATCHED</span>
                      : <span className="text-zinc-400">{r.status?.toUpperCase()}</span>}
                  </td>
                  <td className="py-3">
                    {r.status !== "removed" && (
                      <button onClick={()=>markRemoved(r.id)} data-testid={`mark-removed-${r.id}`} className="font-mono text-xs text-[#00FF41] hover:text-white">MARK REMOVED</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </DashboardLayout>
  );
}
