import React, { useEffect, useState } from "react";
import DashboardLayout from "@/components/DashboardLayout";
import api from "@/lib/api";
import { Link } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { motion } from "framer-motion";
import { Play, AlertTriangle, FileSignature, Sparkles } from "lucide-react";
import { LineChart, Line, ResponsiveContainer, BarChart, Bar, XAxis, Tooltip, Cell } from "recharts";

const SEV_COLOR = { low: "#71717a", medium: "#FFD700", high: "#fb923c", critical: "#FF3333" };

const ScoreGauge = ({ score }) => {
  const color = score >= 70 ? "#00FF41" : score >= 40 ? "#FFD700" : "#FF3333";
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.4 }}
      className="brutal-card p-8 relative overflow-hidden" data-testid="reputation-gauge">
      <div className="overline mb-3">// reputation score</div>
      <div className="flex items-end gap-4 mb-4">
        <motion.div
          key={score}
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          className="font-display font-black text-7xl tracking-tighter" style={{ color }}>{score}</motion.div>
        <div className="font-mono text-zinc-500 mb-3">/ 100</div>
      </div>
      <div className="h-1 bg-[#222] w-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }} animate={{ width: `${score}%` }} transition={{ duration: 0.8, ease: "easeOut" }}
          className="h-1" style={{ background: color }} />
      </div>
      <div className="mt-3 font-mono text-xs text-zinc-500">{score >= 70 ? "EXPOSURE: LOW" : score >= 40 ? "EXPOSURE: MODERATE" : "EXPOSURE: CRITICAL"}</div>

      {/* glowing ring */}
      <motion.div
        animate={{ opacity: [0.05, 0.15, 0.05] }} transition={{ duration: 3, repeat: Infinity }}
        className="absolute -bottom-20 -right-20 w-48 h-48 rounded-full pointer-events-none"
        style={{ background: `radial-gradient(circle, ${color} 0%, transparent 70%)` }}
      />
    </motion.div>
  );
};

const Stat = ({ label, value, accent, testid, delay = 0 }) => (
  <motion.div
    initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay }}
    className="brutal-card p-6" data-testid={testid}>
    <div className="overline mb-2">{label}</div>
    <div className="font-display font-black text-4xl" style={{ color: accent || "#fff" }}>{value}</div>
  </motion.div>
);

export default function Dashboard() {
  const { user } = useAuth();
  const [score, setScore] = useState(null);
  const [findings, setFindings] = useState([]);
  const [scanning, setScanning] = useState(false);
  const [msg, setMsg] = useState("");

  const load = async () => {
    const [r1, r2] = await Promise.all([api.get("/reputation"), api.get("/findings")]);
    setScore(r1.data);
    setFindings(r2.data.findings);
  };
  useEffect(() => { load(); }, []);

  const runScan = async () => {
    setScanning(true); setMsg("");
    try {
      const r = await api.post("/scan/run", {});
      setMsg(r.data.message);
      setTimeout(load, 3000);
    } catch (e) { setMsg(e.response?.data?.detail || "Scan failed"); }
    finally { setScanning(false); }
  };

  if (!score) return <DashboardLayout title="Overview"><div className="font-mono">loading<span className="blink">_</span></div></DashboardLayout>;

  const subActive = user?.subscription_status === "active";
  const recent = findings.slice(0, 6);

  // Trend chart: findings discovered per day for last 14 days
  const trend = (() => {
    const map = new Map();
    for (let i = 13; i >= 0; i--) {
      const d = new Date(); d.setDate(d.getDate() - i);
      map.set(d.toISOString().slice(0, 10), 0);
    }
    findings.forEach(f => {
      const k = (f.discovered_at || "").slice(0, 10);
      if (map.has(k)) map.set(k, map.get(k) + 1);
    });
    return Array.from(map.entries()).map(([d, c]) => ({ d: d.slice(5), c }));
  })();

  // Severity distribution
  const sevDist = ["critical","high","medium","low"].map(s => ({
    name: s.toUpperCase(),
    value: findings.filter(f => f.severity === s && f.status === "active").length,
    color: SEV_COLOR[s],
  }));

  // Broker breakdown (top 6)
  const brokerCount = findings.reduce((acc, f) => { acc[f.broker] = (acc[f.broker]||0)+1; return acc; }, {});
  const topBrokers = Object.entries(brokerCount).sort((a,b)=>b[1]-a[1]).slice(0, 6).map(([n,c]) => ({ name: n, c }));

  return (
    <DashboardLayout title={`Welcome back, ${user?.name || user?.email}`}>
      {!subActive && (
        <motion.div
          initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
          className="brutal-card border-[#FFD700] p-6 mb-6 flex flex-col gap-4" data-testid="trial-banner">
          <div className="flex items-center gap-4">
            <AlertTriangle className="text-[#FFD700]" />
            <div>
              <div className="font-display font-bold flex items-center gap-2">
                <Sparkles size={16} className="text-[#FFD700]"/>
                You&apos;re on a free trial — we&apos;re scanning Google &amp; Bing right now.
              </div>
              <div className="font-mono text-xs text-zinc-500 mt-1">Subscribe to unlock unlimited scans, alerts, removal requests, and legal document generation.</div>
            </div>
          </div>
          <div className="rounded border border-[#FF3333] bg-[#1a0808] p-4 font-mono text-sm text-zinc-200">
            Canada Day Launch Special: Use <span className="text-white font-bold">OCanada75</span> for <span className="text-[#FF3333]">75% off for the entire year</span> on new signups when activated in the registration form.
          </div>
          <Link to="/billing" data-testid="upgrade-cta" className="brutal-btn brutal-btn-primary self-start">Upgrade →</Link>
        </motion.div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <ScoreGauge score={score.score} />
        <Stat label="Active Findings" value={score.breakdown.active} accent="#FF3333" testid="stat-active" delay={0.1} />
        <Stat label="Removed" value={score.breakdown.removed} accent="#00FF41" testid="stat-removed" delay={0.15} />
        <Stat label="Pending Removal" value={score.breakdown.pending_removal} accent="#FFD700" testid="stat-pending" delay={0.2} />
        <Stat label="High Severity" value={score.breakdown.high_severity} accent="#FF3333" testid="stat-high-sev" delay={0.25} />
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
          className="brutal-card p-6 flex flex-col justify-between">
          <div>
            <div className="overline mb-2">// run new scan</div>
            <div className="font-mono text-xs text-zinc-500">Trigger immediate crawl across all brokers + Google &amp; Bing.</div>
          </div>
          <button data-testid="run-scan-btn" disabled={scanning} onClick={runScan} className="brutal-btn brutal-btn-primary mt-4 flex items-center gap-2 justify-center">
            <Play size={14} /> {scanning ? "Scanning..." : "Run Scan Now"}
          </button>
          {msg && <div className="mt-2 font-mono text-xs text-zinc-400" data-testid="scan-message">› {msg}</div>}
        </motion.div>
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.35 }}
          className="brutal-card p-6" data-testid="trend-chart">
          <div className="overline mb-3">// findings · last 14 days</div>
          <div className="h-44">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trend} margin={{ top: 10, right: 10, bottom: 0, left: -25 }}>
                <XAxis dataKey="d" tick={{ fill: "#71717a", fontSize: 10, fontFamily: "JetBrains Mono" }} axisLine={{ stroke: "#222" }} tickLine={false} />
                <Tooltip contentStyle={{ background: "#0a0a0a", border: "1px solid #222", fontFamily: "JetBrains Mono", fontSize: 12 }} labelStyle={{ color: "#fff" }} />
                <Line type="monotone" dataKey="c" stroke="#FF3333" strokeWidth={2} dot={{ fill: "#FF3333", r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}
          className="brutal-card p-6" data-testid="severity-chart">
          <div className="overline mb-3">// active by severity</div>
          <div className="h-44">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sevDist} margin={{ top: 10, right: 10, bottom: 0, left: -25 }}>
                <XAxis dataKey="name" tick={{ fill: "#71717a", fontSize: 10, fontFamily: "JetBrains Mono" }} axisLine={{ stroke: "#222" }} tickLine={false} />
                <Tooltip contentStyle={{ background: "#0a0a0a", border: "1px solid #222", fontFamily: "JetBrains Mono", fontSize: 12 }} labelStyle={{ color: "#fff" }} />
                <Bar dataKey="value">
                  {sevDist.map((e, i) => <Cell key={i} fill={e.color} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>
      </div>

      {/* Top brokers + Legal CTA */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.45 }}
          className="brutal-card p-6 lg:col-span-2" data-testid="top-brokers">
          <div className="overline mb-3">// top exposures by broker</div>
          {topBrokers.length === 0 ? (
            <div className="font-mono text-zinc-500 py-3">No data yet — run a scan.</div>
          ) : (
            <div className="space-y-2">
              {topBrokers.map(({ name, c }) => (
                <div key={name} className="flex items-center gap-4">
                  <div className="font-mono text-xs w-44 truncate">{name}</div>
                  <div className="flex-1 h-3 bg-[#0a0a0a] border border-[#222]">
                    <motion.div initial={{ width: 0 }} animate={{ width: `${(c / Math.max(...topBrokers.map(b=>b.c))) * 100}%` }} transition={{ duration: 0.7 }}
                      className="h-full bg-[#FF3333]" />
                  </div>
                  <div className="font-mono text-xs text-zinc-400 w-8 text-right">{c}</div>
                </div>
              ))}
            </div>
          )}
        </motion.div>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}
          className="brutal-card p-6 border-[#FF3333]/40 bg-gradient-to-br from-[#0a0a0a] to-[#1a0808]">
          <FileSignature className="text-[#FF3333] mb-3" size={20} />
          <div className="font-display font-black text-xl mb-2">Generate Legal Documents</div>
          <div className="font-mono text-xs text-zinc-400 mb-4 leading-relaxed">
            DMCA takedowns, Cease &amp; Desist, CCPA/PIPEDA removal requests — pre-filled and e-signed.
            🇨🇦 🇺🇸 🇲🇽
          </div>
          <Link to="/documents" data-testid="dashboard-docs-cta" className="brutal-btn brutal-btn-primary w-full block text-center">
            Open Documents →
          </Link>
        </motion.div>
      </div>

      {/* Recent findings */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.55 }}
        className="brutal-card p-6">
        <div className="overline mb-3">// recent findings</div>
        {recent.length === 0 ? (
          <div className="font-mono text-zinc-500 py-6">No findings yet. Trial scan is in progress — refresh in a few seconds.</div>
        ) : (
          <table className="w-full" data-testid="recent-findings-table">
            <thead><tr className="border-b border-[#222]">
              {["Broker","Keyword","Data","Severity","Date"].map(h=><th key={h} className="overline text-left py-2">{h}</th>)}
            </tr></thead>
            <tbody>
              {recent.map(f => (
                <tr key={f.id} className="border-b border-[#222] hover:bg-[#0a0a0a]">
                  <td className="py-3 font-mono text-sm">{f.broker}</td>
                  <td className="py-3 font-mono text-sm text-zinc-400">{f.keyword_value}</td>
                  <td className="py-3 font-mono text-xs text-zinc-500">{(f.data_found || []).join(", ")}</td>
                  <td className={`py-3 font-mono text-sm severity-${f.severity}`}>{(f.severity || "").toUpperCase()}</td>
                  <td className="py-3 font-mono text-xs text-zinc-500">{f.discovered_at?.slice(0,10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="mt-4"><Link to="/findings" data-testid="view-all-findings" className="font-mono text-sm text-[#FF3333] hover:text-white">view all findings →</Link></div>
      </motion.div>
    </DashboardLayout>
  );
}
