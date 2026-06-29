import React, { useCallback, useEffect, useState } from "react";
import DashboardLayout from "@/components/DashboardLayout";
import AdminTable from "@/components/AdminTable";
import Drawer, { Field } from "@/components/Drawer";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useNavigate } from "react-router-dom";
import { CheckCircle2, XCircle, UserX, KeyRound, Play, LogIn, Trash2, ShieldCheck, ShieldOff, Eye } from "lucide-react";
import AdminAnalytics from "@/components/AdminAnalytics";
import AdminHealth from "@/components/AdminHealth";
import AdminBrokerContacts from "@/components/AdminBrokerContacts";
import AdminSettings from "@/components/AdminSettings";
import AdminOperations from "@/components/AdminOperations";
import AdminSupportPanel from "@/components/AdminSupportPanel";
import AdminWorkforcePanel from "@/components/AdminWorkforcePanel";

const Stat = ({ label, value, testid }) => (
  <div className="brutal-card p-5" data-testid={testid}>
    <div className="overline mb-2">{label}</div>
    <div className="font-display font-black text-3xl">{value}</div>
  </div>
);

const STATUS_PILL = (status, color) => (
  <span className="font-mono text-[10px] px-2 py-0.5 border" style={{ color, borderColor: color }}>{status}</span>
);

const EMPTY_STATS = {
  users: 0,
  active_subs: 0,
  keywords: 0,
  findings_total: 0,
  findings_active: 0,
  pending_payments: 0,
  removal_requests: 0,
};

export default function Admin() {
  const { user: me, logout } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [tab, setTab] = useState("payments");
  const [users, setUsers] = useState([]);
  const [payments, setPayments] = useState([]);
  const [emails, setEmails] = useState([]);
  const [removals, setRemovals] = useState([]);
  const [audit, setAudit] = useState([]);
  const [authEvents, setAuthEvents] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [authEventsLoading, setAuthEventsLoading] = useState(false);
  const [authEventsError, setAuthEventsError] = useState("");

  // Detail drawer state
  const [userDetail, setUserDetail] = useState(null);
  const [paymentDetail, setPaymentDetail] = useState(null);
  const [removalDetail, setRemovalDetail] = useState(null);
  const [documentDetail, setDocumentDetail] = useState(null);
  const [authEventDetail, setAuthEventDetail] = useState(null);

  const normalizeDetail = useCallback((detail) => {
    const raw = String(detail || "");
    const lower = raw.toLowerCase();
    if (lower.includes("no matching row found") || lower.includes("no row was found")) {
      return "No records available yet.";
    }
    return raw || "Request failed.";
  }, []);

  const loadAuthEvents = useCallback(async () => {
    setAuthEventsLoading(true);
    setAuthEventsError("");
    try {
      const r = await api.get("/auth/audit/events?limit=500");
      setAuthEvents(r.data?.events || []);
    } catch (e) {
      setAuthEventsError(normalizeDetail(e?.response?.data?.detail || e?.message || "Failed to load auth audit events"));
    } finally {
      setAuthEventsLoading(false);
    }
  }, [normalizeDetail]);

  const load = useCallback(async () => {
    const keys = ["stats", "users", "payments", "email-log", "removals", "audit-log", "documents"];
    const results = await Promise.allSettled(keys.map((k) => api.get(`/admin/${k}`)));

    const dataFor = (idx, fallback) => {
      const res = results[idx];
      if (res.status !== "fulfilled") return fallback;
      return res.value?.data ?? fallback;
    };

    const failed = results
      .map((res, idx) => ({ res, idx }))
      .filter(({ res }) => res.status === "rejected")
      .map(({ res, idx }) => {
        const detail = normalizeDetail(res.reason?.response?.data?.detail || res.reason?.message || "");
        return `${keys[idx]}: ${detail}`;
      })
      .filter((m) => !m.toLowerCase().includes("no records available yet"));

    const s = dataFor(0, EMPTY_STATS);
    const u = dataFor(1, {});
    const p = dataFor(2, {});
    const e = dataFor(3, {});
    const r = dataFor(4, {});
    const a = dataFor(5, {});
    const d = dataFor(6, {});

    setStats(s || EMPTY_STATS);
    setUsers(u.users || []);
    setPayments(p.payments || []);
    setEmails(e.emails || []);
    setRemovals(r.removals || []);
    setAudit(a.audit || []);
    setDocuments(d.documents || []);
    setLoadError(failed.length ? failed[0] : "");

    loadAuthEvents();
  }, [loadAuthEvents, normalizeDetail]);
  useEffect(() => { load(); }, [load]);

  const userById = (id) => users.find(u => u.id === id);

  // ── Payment actions ─────────────────────────────────────────
  const confirmPayment = async (id) => { await api.post(`/admin/payments/${id}/confirm`); load(); setPaymentDetail(null); };
  const rejectPayment  = async (id) => { await api.post(`/admin/payments/${id}/reject`);  load(); setPaymentDetail(null); };

  // ── Removal actions ─────────────────────────────────────────
  const markRemoved = async (id) => { await api.post(`/admin/removals/${id}/mark-removed`); load(); setRemovalDetail(null); };

  // ── User actions ─────────────────────────────────────────────
  const openUser = async (u) => {
    const r = await api.get(`/admin/users/${u.id}`);
    setUserDetail(r.data.user);
  };
  const patchUser = async (id, changes) => {
    await api.patch(`/admin/users/${id}`, changes);
    const r = await api.get(`/admin/users/${id}`); setUserDetail(r.data.user);
    load();
  };
  const deleteUser = async (u) => {
    if (!window.confirm(`PERMANENTLY delete ${u.email}? This cascades all their findings, payments, documents.`)) return;
    await api.delete(`/admin/users/${u.id}`);
    setUserDetail(null); load();
  };
  const resetPassword = async (u) => {
    const np = window.prompt(`New password for ${u.email}? (min 6 chars)`, "");
    if (!np || np.length < 6) return;
    await api.post(`/admin/users/${u.id}/reset-password`, { new_password: np });
    alert(`Password reset. New password emailed/communicated to ${u.email}.`);
  };
  const triggerScan = async (u) => {
    await api.post(`/admin/users/${u.id}/scan`);
    alert(`Scan queued for ${u.email}.`);
    load();
  };
  const impersonate = async (u) => {
    if (!window.confirm(`Impersonate ${u.email}? Your current admin session will be replaced. You'll need to logout and log back in to return.`)) return;
    const r = await api.post(`/admin/users/${u.id}/impersonate`);
    localStorage.setItem("d31337m3_token", r.data.token);
    alert(`Now impersonating ${u.email}. Navigating to their dashboard…`);
    window.location.href = "/dashboard";
  };

  if (!stats) return <DashboardLayout title="Admin"><div className="font-mono">loading<span className="blink">_</span></div></DashboardLayout>;

  // ── Column definitions ─────────────────────────────────────
  const paymentColumns = [
    { key: "created_at", label: "Date", render: r => <span className="text-zinc-500">{r.created_at?.slice(0,16)}</span>, csv: r => r.created_at?.slice(0,16) },
    { key: "user_email", label: "User", render: r => userById(r.user_id)?.email || r.user_id?.slice(0,8), csv: r => userById(r.user_id)?.email || r.user_id },
    { key: "plan_id", label: "Plan", render: r => <span className="text-white">{r.plan_id}</span> },
    { key: "method", label: "Method" },
    { key: "amount_usd", label: "Amount", render: r => `$${r.amount_usd}` },
    { key: "status", label: "Status", render: r => {
        const color = r.status === "confirmed" ? "#00FF41" : r.status === "rejected" ? "#FF3333" : "#FFD700";
        return STATUS_PILL(r.status?.toUpperCase(), color);
      }},
    { key: "tx_hash", label: "TX", render: r => <span className="text-zinc-500">{r.tx_hash?.slice(0,12) || "—"}</span>, csv: r => r.tx_hash || "" },
  ];
  const paymentFilters = [
    { key: "status", label: "status", options: [
      { value: "awaiting_confirmation", label: "Awaiting Interac" },
      { value: "awaiting_tx_hash", label: "Awaiting TX" },
      { value: "pending_manual_review", label: "Pending Review" },
      { value: "pending_paypal_capture", label: "Pending PayPal" },
      { value: "confirmed", label: "Confirmed" },
      { value: "rejected", label: "Rejected" },
    ]},
    { key: "method", label: "method", options: [
      { value: "interac", label: "Interac" },
      { value: "crypto", label: "Crypto" },
      { value: "paypal", label: "PayPal" },
    ]},
  ];

  const removalColumns = [
    { key: "created_at", label: "Date", render: r => <span className="text-zinc-500">{r.created_at?.slice(0,16)}</span> },
    { key: "user_email", label: "User" },
    { key: "broker", label: "Broker", render: r => <span className="text-white">{r.broker}</span> },
    { key: "broker_email", label: "Dispatched To", render: r => r.broker_email || "—" },
    { key: "status", label: "Status", render: r => {
        const color = r.status === "removed" ? "#00FF41" : r.status === "dispatched" ? "#FFD700" : "#A1A1AA";
        return STATUS_PILL(r.status?.toUpperCase(), color);
      }},
  ];
  const removalFilters = [
    { key: "status", label: "status", options: [
      { value: "submitted", label: "Submitted" },
      { value: "dispatched", label: "Dispatched" },
      { value: "removed", label: "Removed" },
    ]},
  ];

  const userColumns = [
    { key: "created_at", label: "Joined", render: r => <span className="text-zinc-500">{r.created_at?.slice(0,10)}</span> },
    { key: "email", label: "Email", render: r => <span className="text-white">{r.email}</span> },
    { key: "name", label: "Name" },
    { key: "auth_provider", label: "Provider" },
    { key: "plan_id", label: "Plan", render: r => r.plan_id?.toUpperCase() || "—" },
    { key: "subscription_status", label: "Sub", render: r => {
        const color = r.subscription_status === "active" ? "#00FF41" : r.subscription_status === "suspended" ? "#FF3333" : "#A1A1AA";
        return STATUS_PILL(r.subscription_status?.toUpperCase(), color);
      }},
    { key: "is_admin", label: "Admin", render: r => r.is_admin ? <ShieldCheck size={14} className="text-[#FF3333]"/> : "—", csv: r => r.is_admin ? "YES" : "" },
    { key: "is_active", label: "Active", render: r => r.is_active === false ? <span className="text-[#FF3333]">SUSPENDED</span> : <span className="text-[#00FF41]">YES</span> },
  ];
  const userFilters = [
    { key: "subscription_status", label: "sub", options: [
      { value: "trial", label: "Trial" }, { value: "active", label: "Active" },
      { value: "suspended", label: "Suspended" }, { value: "cancelled", label: "Cancelled" },
    ]},
    { key: "plan_id", label: "plan", options: [
      { value: "basic", label: "Basic" }, { value: "pro", label: "Pro" }, { value: "enterprise", label: "Enterprise" },
    ]},
  ];

  const emailColumns = [
    { key: "sent_at", label: "Sent", render: r => <span className="text-zinc-500">{r.sent_at?.slice(0,16)}</span> },
    { key: "to", label: "To" },
    { key: "subject", label: "Subject", render: r => <span className="text-white">{r.subject}</span> },
    { key: "delivered", label: "Status", render: r => {
        if (r.mocked) return STATUS_PILL("MOCKED", "#A1A1AA");
        if (r.delivered) return STATUS_PILL("SENT", "#00FF41");
        return STATUS_PILL("FAILED", "#FF3333");
      }, csv: r => r.mocked ? "MOCKED" : r.delivered ? "SENT" : "FAILED" },
  ];

  const auditColumns = [
    { key: "at", label: "When", render: r => <span className="text-zinc-500">{r.at?.slice(0,19)}</span> },
    { key: "actor_email", label: "Admin" },
    { key: "action", label: "Action", render: r => <span className="text-[#FF3333]">{r.action}</span> },
    { key: "target_email", label: "Target", render: r => r.target_email || r.target_user_id?.slice(0,8) || "—" },
    { key: "changes", label: "Changes", render: r => <span className="text-zinc-400">{r.changes ? JSON.stringify(r.changes).slice(0,80) : "—"}</span>, csv: r => JSON.stringify(r.changes || {}) },
  ];

  const authEventColumns = [
    { key: "created_at", label: "When", render: r => <span className="text-zinc-500">{r.created_at?.slice(0,19)}</span>, csv: r => r.created_at || "" },
    { key: "event", label: "Event", render: r => <span className="text-[#FF3333]">{r.event}</span> },
    { key: "email", label: "Email", render: r => r.email || "—" },
    { key: "user_id", label: "User", render: r => r.user_id ? <span className="text-zinc-300">{r.user_id.slice(0,8)}</span> : "—", csv: r => r.user_id || "" },
    { key: "ip_address", label: "IP", render: r => r.ip_address || "—" },
    { key: "detail", label: "Detail", render: r => <span className="text-zinc-400">{r.detail ? JSON.stringify(r.detail).slice(0,120) : "—"}</span>, csv: r => JSON.stringify(r.detail || {}) },
  ];

  const eventOptions = Array.from(new Set(authEvents.map((r) => r.event).filter(Boolean)))
    .sort()
    .map((v) => ({ value: v, label: v }));
  const userOptions = Array.from(new Set(authEvents.map((r) => r.user_id).filter(Boolean)))
    .sort()
    .map((v) => ({ value: v, label: `${v.slice(0,8)}...` }));
  const emailOptions = Array.from(new Set(authEvents.map((r) => r.email).filter(Boolean)))
    .sort()
    .map((v) => ({ value: v, label: v }));
  const authEventFilters = [
    { key: "event", label: "event", options: eventOptions },
    { key: "user_id", label: "user", options: userOptions },
    { key: "email", label: "email", options: emailOptions },
  ];

  const documentColumns = [
    { key: "created_at", label: "Created", render: r => <span className="text-zinc-500">{r.created_at?.slice(0,16)}</span> },
    { key: "user_email", label: "User" },
    { key: "title", label: "Template", render: r => <span className="text-white">{r.title}</span> },
    { key: "recipient_broker", label: "Recipient" },
    { key: "country", label: "Country" },
    { key: "status", label: "Status", render: r => STATUS_PILL(r.status?.toUpperCase(), r.status === "signed" ? "#00FF41" : "#FFD700") },
    { key: "dispatched_to", label: "Dispatched", render: r => r.dispatched_to ? <span className="text-[#00FF41]">{r.dispatched_to}</span> : "—" },
  ];
  const documentFilters = [
    { key: "status", label: "status", options: [
      { value: "draft", label: "Draft" },
      { value: "signed", label: "Signed" },
    ]},
    { key: "country", label: "country", options: [
      { value: "CA", label: "🇨🇦 Canada" },
      { value: "US", label: "🇺🇸 USA" },
      { value: "MX", label: "🇲🇽 México" },
    ]},
  ];

  const openDocument = async (d) => {
    const r = await api.get(`/admin/documents/${d.id}`);
    setDocumentDetail(r.data.document);
  };

  return (
    <DashboardLayout title="Admin Console">
      {loadError && (
        <div className="mb-4 font-mono text-xs text-[#FF3333]" data-testid="admin-load-error">
          {'> '} {loadError}
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-6">
        <Stat label="Users" value={stats.users} testid="admin-stat-users" />
        <Stat label="Active Subs" value={stats.active_subs} testid="admin-stat-subs" />
        <Stat label="Keywords" value={stats.keywords} testid="admin-stat-keywords" />
        <Stat label="Findings" value={stats.findings_total} testid="admin-stat-findings" />
        <Stat label="Active" value={stats.findings_active} testid="admin-stat-findings-active" />
        <Stat label="Pending Pays" value={stats.pending_payments} testid="admin-stat-pending-payments" />
        <Stat label="Removals" value={stats.removal_requests} testid="admin-stat-removals" />
      </div>

      <div className="flex gap-2 mb-4 flex-wrap" data-testid="admin-tabs">
        {[
          ["operations","Operations"],
          ["analytics","Analytics"],
          ["health","Health"],
          ["payments","Payments"],
          ["removals","Removals"],
          ["users","Users"],
          ["documents","Documents"],
          ["brokers","Brokers"],
          ["support","Support"],
          ["workforce","Workforce Ops"],
          ["emails","Email Log"],
          ["audit","Audit Log"],
          ["auth-security","Auth Security"],
          ["settings","Settings"],
        ].map(([k,l]) => (
          <button key={k} onClick={()=>setTab(k)} data-testid={`admin-tab-${k}`}
            className={`font-mono text-xs px-4 py-2 border ${tab===k ? "border-white text-white" : "border-[#222] text-zinc-500 hover:text-white"}`}>
            {l.toUpperCase()}
          </button>
        ))}
      </div>

      {tab === "analytics" && <AdminAnalytics />}
      {tab === "operations" && <AdminOperations />}
      {tab === "health" && <AdminHealth />}
      {tab === "brokers" && <AdminBrokerContacts />}
      {tab === "support" && <AdminSupportPanel />}
      {tab === "workforce" && <AdminWorkforcePanel />}
      {tab === "settings" && <AdminSettings />}

      {tab === "payments" && (
        <AdminTable
          testid="admin-payments" exportName="payments"
          data={payments} columns={paymentColumns} filters={paymentFilters}
          searchKeys={["plan_id", "method", "status", "tx_hash"]}
          onRowClick={(r) => setPaymentDetail(r)}
        />
      )}
      {tab === "removals" && (
        <AdminTable
          testid="admin-removals" exportName="removals"
          data={removals} columns={removalColumns} filters={removalFilters}
          searchKeys={["broker", "broker_email", "user_email", "status"]}
          onRowClick={(r) => setRemovalDetail(r)}
        />
      )}
      {tab === "users" && (
        <AdminTable
          testid="admin-users" exportName="users"
          data={users} columns={userColumns} filters={userFilters}
          searchKeys={["email", "name", "id"]}
          onRowClick={openUser}
        />
      )}
      {tab === "emails" && (
        <AdminTable
          testid="admin-emails" exportName="email-log"
          data={emails} columns={emailColumns}
          searchKeys={["to", "subject"]}
        />
      )}
      {tab === "audit" && (
        <AdminTable
          testid="admin-audit" exportName="audit-log"
          data={audit} columns={auditColumns}
          searchKeys={["actor_email", "action", "target_email"]}
        />
      )}
      {tab === "auth-security" && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="font-mono text-xs text-zinc-500">Auth login/register/2FA/device security trail</div>
            <button
              onClick={loadAuthEvents}
              disabled={authEventsLoading}
              data-testid="admin-auth-audit-refresh"
              className="brutal-btn !py-2 !px-3"
            >
              {authEventsLoading ? "Refreshing..." : "Refresh"}
            </button>
          </div>
          {authEventsError && (
            <div className="mb-3 font-mono text-xs text-[#FF3333]" data-testid="admin-auth-audit-error">
              {'> '} {authEventsError}
            </div>
          )}
          <AdminTable
            testid="admin-auth-audit"
            exportName="auth-audit-events"
            data={authEvents}
            columns={authEventColumns}
            filters={authEventFilters}
            searchKeys={["event", "email", "user_id", "ip_address"]}
            onRowClick={(r) => setAuthEventDetail(r)}
          />
        </div>
      )}
      {tab === "documents" && (
        <AdminTable
          testid="admin-documents" exportName="documents"
          data={documents} columns={documentColumns} filters={documentFilters}
          searchKeys={["title", "user_email", "recipient_broker", "country"]}
          onRowClick={openDocument}
        />
      )}

      {/* Payment drawer */}
      <Drawer open={!!paymentDetail} onClose={() => setPaymentDetail(null)} title={paymentDetail ? `Payment · $${paymentDetail.amount_usd}` : ""} testid="payment-drawer">
        {paymentDetail && (
          <div className="space-y-1">
            <Field label="Payment ID" value={paymentDetail.id} />
            <Field label="User" value={userById(paymentDetail.user_id)?.email || paymentDetail.user_id} />
            <Field label="Plan" value={paymentDetail.plan_id?.toUpperCase()} />
            <Field label="Method" value={paymentDetail.method} />
            <Field label="Amount" value={`$${paymentDetail.amount_usd} USD`} />
            <Field label="Status" value={paymentDetail.status} />
            <Field label="Created" value={paymentDetail.created_at} />
            {paymentDetail.tx_hash && <Field label="TX Hash" value={paymentDetail.tx_hash} />}
            {paymentDetail.network && <Field label="Network" value={paymentDetail.network} />}
            {paymentDetail.instructions && <Field label="Instructions" value={<pre className="text-xs whitespace-pre-wrap">{JSON.stringify(paymentDetail.instructions, null, 2)}</pre>} />}
            {paymentDetail.verification && <Field label="Verification" value={<pre className="text-xs whitespace-pre-wrap">{JSON.stringify(paymentDetail.verification, null, 2)}</pre>} />}
            {!["confirmed","rejected"].includes(paymentDetail.status) && (
              <div className="flex gap-3 mt-6">
                <button onClick={() => confirmPayment(paymentDetail.id)} data-testid="drawer-confirm-payment" className="brutal-btn brutal-btn-primary flex items-center gap-2"><CheckCircle2 size={14}/>Confirm Payment</button>
                <button onClick={() => rejectPayment(paymentDetail.id)} data-testid="drawer-reject-payment" className="brutal-btn flex items-center gap-2"><XCircle size={14}/>Reject</button>
              </div>
            )}
          </div>
        )}
      </Drawer>

      {/* Removal drawer */}
      <Drawer open={!!removalDetail} onClose={() => setRemovalDetail(null)} title={removalDetail ? `Removal · ${removalDetail.broker}` : ""} testid="removal-drawer">
        {removalDetail && (
          <div className="space-y-1">
            <Field label="Removal ID" value={removalDetail.id} />
            <Field label="User" value={removalDetail.user_email} />
            <Field label="Broker" value={removalDetail.broker} />
            <Field label="Privacy Email" value={removalDetail.broker_email} />
            {removalDetail.broker_form && <Field label="Opt-Out Form" value={<a href={removalDetail.broker_form} target="_blank" rel="noopener noreferrer" className="text-[#FF3333] hover:underline">{removalDetail.broker_form}</a>} />}
            <Field label="Status" value={removalDetail.status} />
            <Field label="Created" value={removalDetail.created_at} />
            {removalDetail.dispatched_at && <Field label="Dispatched" value={removalDetail.dispatched_at} />}
            {removalDetail.dispatched_document_id && <Field label="Document ID" value={removalDetail.dispatched_document_id} />}
            {removalDetail.status !== "removed" && (
              <button onClick={() => markRemoved(removalDetail.id)} data-testid="drawer-mark-removed" className="brutal-btn brutal-btn-primary mt-6 flex items-center gap-2"><CheckCircle2 size={14}/>Mark as Removed</button>
            )}
          </div>
        )}
      </Drawer>

      {/* User drawer */}      <Drawer open={!!userDetail} onClose={() => setUserDetail(null)} title={userDetail ? userDetail.email : ""} testid="user-drawer">
        {userDetail && (
          <div className="space-y-1">
            <Field label="User ID" value={userDetail.id} />
            <Field label="Email" value={userDetail.email} />
            <Field label="Name" value={userDetail.name} />
            <Field label="Auth Provider" value={userDetail.auth_provider} />
            <Field label="Created" value={userDetail.created_at} />

            <div className="grid grid-cols-5 gap-2 mt-4 mb-4">
              <Stat label="Keywords"  value={userDetail._keywords_count}  testid="ud-kw" />
              <Stat label="Findings"  value={userDetail._findings_count}  testid="ud-fn" />
              <Stat label="Payments"  value={userDetail._payments_count}  testid="ud-pm" />
              <Stat label="Docs"      value={userDetail._documents_count} testid="ud-dc" />
              <Stat label="Removals"  value={userDetail._removals_count}  testid="ud-rm" />
            </div>

            {/* Editable fields */}
            <div className="border border-[#222] p-4 bg-black/50 mt-4">
              <div className="overline mb-3">// edit</div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="overline mb-1">plan</div>
                  <select data-testid="ud-plan" value={userDetail.plan_id || ""} onChange={(e) => patchUser(userDetail.id, { plan_id: e.target.value })} className="brutal-input">
                    <option value="">— none —</option>
                    <option value="basic">Basic</option><option value="pro">Pro</option><option value="enterprise">Enterprise</option>
                  </select>
                </div>
                <div>
                  <div className="overline mb-1">subscription status</div>
                  <select data-testid="ud-sub" value={userDetail.subscription_status || ""} onChange={(e) => patchUser(userDetail.id, { subscription_status: e.target.value })} className="brutal-input">
                    <option value="trial">Trial</option><option value="active">Active</option>
                    <option value="suspended">Suspended</option><option value="cancelled">Cancelled</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="grid grid-cols-2 gap-3 mt-6">
              <button onClick={() => triggerScan(userDetail)} data-testid="ud-scan" className="brutal-btn flex items-center gap-2 justify-center"><Play size={14}/>Trigger Scan</button>
              <button onClick={() => resetPassword(userDetail)} data-testid="ud-reset-pw" className="brutal-btn flex items-center gap-2 justify-center"><KeyRound size={14}/>Reset Password</button>
              <button
                onClick={() => patchUser(userDetail.id, { is_active: !(userDetail.is_active === false ? false : true) })}
                data-testid="ud-toggle-active"
                className="brutal-btn flex items-center gap-2 justify-center"
              >{userDetail.is_active === false ? <><ShieldCheck size={14}/>Reactivate</> : <><UserX size={14}/>Suspend</>}</button>
              <button
                onClick={() => patchUser(userDetail.id, { is_admin: !userDetail.is_admin })}
                disabled={userDetail.id === me?.id}
                data-testid="ud-toggle-admin"
                className="brutal-btn flex items-center gap-2 justify-center"
              >{userDetail.is_admin ? <><ShieldOff size={14}/>Revoke Admin</> : <><ShieldCheck size={14}/>Make Admin</>}</button>
              <button onClick={() => impersonate(userDetail)} disabled={userDetail.id === me?.id} data-testid="ud-impersonate" className="brutal-btn flex items-center gap-2 justify-center"><LogIn size={14}/>Impersonate</button>
              <button onClick={() => deleteUser(userDetail)} disabled={userDetail.id === me?.id} data-testid="ud-delete" className="brutal-btn !border-[#FF3333] !text-[#FF3333] hover:!bg-[#FF3333] hover:!text-white flex items-center gap-2 justify-center"><Trash2 size={14}/>Delete User</button>
            </div>
          </div>
        )}
      </Drawer>

      {/* Document drawer */}
      <Drawer open={!!documentDetail} onClose={() => setDocumentDetail(null)} title={documentDetail ? documentDetail.title : ""} testid="document-drawer">
        {documentDetail && (
          <div className="space-y-1">
            <Field label="Document ID" value={documentDetail.id} />
            <Field label="User" value={documentDetail._user?.email} />
            <Field label="Template" value={documentDetail.template_id} />
            <Field label="Recipient" value={documentDetail.recipient_broker} />
            <Field label="Country" value={documentDetail.country} />
            <Field label="Status" value={documentDetail.status?.toUpperCase()} />
            <Field label="Created" value={documentDetail.created_at} />
            {documentDetail.signed_at && <Field label="Signed" value={`${documentDetail.signed_name} · ${documentDetail.signed_at}`} />}
            {documentDetail.dispatched_to && <Field label="Dispatched To" value={<span className="text-[#00FF41]">{documentDetail.dispatched_to}</span>} />}
            <div className="mt-4 border border-[#222] p-4 bg-black">
              <div className="overline mb-2">// body</div>
              <pre className="font-mono text-xs text-zinc-300 whitespace-pre-wrap max-h-96 overflow-y-auto">{documentDetail.body}</pre>
            </div>
            {documentDetail.signature_image && (
              <div className="mt-3 border border-[#222] p-3">
                <div className="overline mb-2">// affixed signature</div>
                <img src={documentDetail.signature_image} alt="sig" className="max-h-20 bg-white p-2 inline-block"/>
              </div>
            )}
          </div>
        )}
      </Drawer>

      {/* Auth event drawer */}
      <Drawer
        open={!!authEventDetail}
        onClose={() => setAuthEventDetail(null)}
        title={authEventDetail ? `Auth Event · ${authEventDetail.event}` : ""}
        testid="auth-event-drawer"
      >
        {authEventDetail && (
          <div className="space-y-1">
            <Field label="Event ID" value={authEventDetail.id} />
            <Field label="When" value={authEventDetail.created_at} />
            <Field label="Event" value={authEventDetail.event} />
            <Field label="Email" value={authEventDetail.email || "—"} />
            <Field label="User ID" value={authEventDetail.user_id || "—"} />
            <Field label="IP Address" value={authEventDetail.ip_address || "—"} />
            <div className="mt-4 border border-[#222] p-4 bg-black">
              <div className="overline mb-2">// detail payload</div>
              <pre className="font-mono text-xs text-zinc-300 whitespace-pre-wrap max-h-96 overflow-y-auto">
                {JSON.stringify(authEventDetail.detail || {}, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </Drawer>
    </DashboardLayout>
  );
}
