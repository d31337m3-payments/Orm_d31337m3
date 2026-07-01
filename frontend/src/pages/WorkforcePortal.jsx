import React, { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { useNavigate, Link } from "react-router-dom";
import { Users, Calendar, Clock, DollarSign, MessageSquare, ShieldAlert } from "lucide-react";

export default function WorkforcePortal() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const [tab, setTab] = useState("shifts");

  useEffect(() => {
    if (loading) return;
    if (!user) { navigate("/login"); return; }
  }, [user, loading, navigate]);

  if (loading) return <div className="min-h-screen bg-[#050505] flex items-center justify-center"><div className="font-mono text-zinc-500">loading...</div></div>;
  if (!user) return null;

  const isStaff = !!user.employee_number;

  return (
    <div className="min-h-screen bg-[#050505] text-white">
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <Link to="/" className="font-mono text-xs text-zinc-500 hover:text-white">← home</Link>
            <h1 className="font-display font-black text-3xl mt-1">Workforce Portal</h1>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-mono text-xs text-zinc-500">{user.email}</span>
            {isStaff && <span className="text-xs text-[#00FF41] font-mono border border-[#00FF41]/30 px-2 py-0.5">EMP {user.employee_number}</span>}
          </div>
        </div>

        {!isStaff && (
          <div className="brutal-card p-8 border border-[#FF3333]/50 text-center">
            <ShieldAlert size={32} className="text-[#FF3333] mx-auto mb-3" />
            <h2 className="font-display font-black text-xl mb-2">Access Restricted</h2>
            <p className="font-mono text-sm text-zinc-400">
              This portal requires an active employee account with a valid employee number.
              Contact your administrator if you believe this is an error.
            </p>
          </div>
        )}

        {isStaff && (
          <>
            <div className="flex gap-2 mb-6 flex-wrap">
              {[
                ["shifts", "Shifts", Calendar],
                ["timesheets", "Timesheets", Clock],
                ["payroll", "Payroll", DollarSign],
                ["comments", "Shift Comments", MessageSquare],
              ].map(([k, l, Icon]) => (
                <button key={k} onClick={() => setTab(k)}
                  className={`font-mono text-xs px-4 py-2 border flex items-center gap-2 ${
                    tab === k ? "border-white text-white" : "border-[#222] text-zinc-500 hover:text-white"
                  }`}>
                  <Icon size={14} /> {l}
                </button>
              ))}
            </div>

            {tab === "shifts" && <ShiftsView />}
            {tab === "timesheets" && <TimesheetsView />}
            {tab === "payroll" && <PayrollView />}
            {tab === "comments" && <ShiftCommentsView />}
          </>
        )}
      </div>
    </div>
  );
}

function ShiftsView() {
  const [shifts, setShifts] = useState([]);
  useEffect(() => {
    import("@/lib/adminApi").then(m => m.default.workforceAdminShifts().then(setShifts).catch(() => {}));
  }, []);
  return (
    <div className="brutal-card p-6">
      <h2 className="font-display font-black text-xl mb-4">Upcoming Shifts</h2>
      {shifts.length === 0 && <p className="font-mono text-sm text-zinc-600">No shifts found.</p>}
      <div className="space-y-2">
        {shifts.map((s) => (
          <div key={s.id} className="flex items-center justify-between font-mono text-xs border border-[#222] p-3">
            <div>
              <span className="text-white">{s.employee_email || s.employee_id}</span>
              <span className="text-zinc-500 ml-3">{s.role || "—"}</span>
            </div>
            <div className="text-zinc-400">
              {s.start_at ? new Date(s.start_at).toLocaleString() : "?"} — {s.end_at ? new Date(s.end_at).toLocaleString() : "?"}
            </div>
            <span className={`px-2 py-0.5 text-xs ${s.status === "completed" ? "text-[#00FF41]" : s.status === "cancelled" ? "text-[#FF3333]" : "text-[#FFD700]"}`}>
              {s.status || "scheduled"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function TimesheetsView() {
  const [timesheets, setTimesheets] = useState([]);
  useEffect(() => {
    import("@/lib/adminApi").then(m => m.default.workforceAdminTimesheets().then(setTimesheets).catch(() => {}));
  }, []);
  return (
    <div className="brutal-card p-6">
      <h2 className="font-display font-black text-xl mb-4">Timesheets</h2>
      {timesheets.length === 0 && <p className="font-mono text-sm text-zinc-600">No timesheet entries.</p>}
      <div className="overflow-x-auto">
        <table className="w-full font-mono text-xs">
          <thead><tr className="text-zinc-500 border-b border-[#222]">
            <th className="text-left py-2">Employee</th><th className="text-left py-2">Date</th><th className="text-right py-2">Hours</th><th className="text-right py-2">OT</th><th className="text-center py-2">Approved</th>
          </tr></thead>
          <tbody>
            {timesheets.map((t) => (
              <tr key={t.id} className="border-b border-[#222]/50">
                <td className="py-2 text-white">{t.employee_email || t.employee_id}</td>
                <td className="py-2 text-zinc-400">{t.date ? new Date(t.date).toLocaleDateString() : "?"}</td>
                <td className="py-2 text-right text-zinc-300">{t.hours}</td>
                <td className="py-2 text-right text-zinc-300">{t.overtime_hours || 0}</td>
                <td className="py-2 text-center">{t.approved ? <span className="text-[#00FF41]">✓</span> : <span className="text-zinc-600">—</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PayrollView() {
  const [runs, setRuns] = useState([]);
  useEffect(() => {
    import("@/lib/adminApi").then(m => m.default.workforceAdminPayrollRuns().then(setRuns).catch(() => {}));
  }, []);
  return (
    <div className="brutal-card p-6">
      <h2 className="font-display font-black text-xl mb-4">Payroll History</h2>
      {runs.length === 0 && <p className="font-mono text-sm text-zinc-600">No payroll runs yet.</p>}
      <div className="space-y-2">
        {runs.map((r) => (
          <div key={r.id} className="flex items-center justify-between font-mono text-xs border border-[#222] p-3">
            <div>
              <span className="text-white">{r.period_start ? new Date(r.period_start).toLocaleDateString() : "?"}</span>
              <span className="text-zinc-500 mx-2">→</span>
              <span className="text-white">{r.period_end ? new Date(r.period_end).toLocaleDateString() : "?"}</span>
            </div>
            <div className="text-zinc-300">${r.total_amount?.toFixed(2) || "0.00"}</div>
            <span className={`px-2 py-0.5 ${r.status === "paid" ? "text-[#00FF41]" : r.status === "draft" ? "text-zinc-500" : "text-[#FFD700]"}`}>
              {r.status || "draft"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ShiftCommentsView() {
  const [shifts, setShifts] = useState([]);
  const [selectedShift, setSelectedShift] = useState(null);
  const [comments, setComments] = useState([]);
  useEffect(() => {
    import("@/lib/adminApi").then(m => m.default.workforceAdminShifts().then(setShifts).catch(() => {}));
  }, []);
  useEffect(() => {
    if (!selectedShift) return;
    import("@/lib/adminApi").then(m => m.default.workforceAdminShifts().then(() => {}).catch(() => {}));
  }, [selectedShift]);
  return (
    <div className="brutal-card p-6">
      <h2 className="font-display font-black text-xl mb-4">Shift Discussions</h2>
      {shifts.length === 0 && <p className="font-mono text-sm text-zinc-600">No shifts to comment on.</p>}
      <div className="space-y-2">
        {shifts.map((s) => (
          <button key={s.id} onClick={() => setSelectedShift(selectedShift === s.id ? null : s.id)}
            className={`w-full text-left font-mono text-xs border p-3 transition-colors ${
              selectedShift === s.id ? "border-[#00FF41] bg-[#00FF41]/5" : "border-[#222] hover:border-zinc-500"
            }`}>
            <span className="text-white">{s.employee_email || s.employee_id}</span>
            <span className="text-zinc-500 ml-3">{s.start_at ? new Date(s.start_at).toLocaleString() : "?"}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
