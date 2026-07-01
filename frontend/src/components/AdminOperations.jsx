import React, { useEffect, useMemo, useState } from "react";
import adminApi from "@/lib/adminApi";
import { Activity, Server, Users, CreditCard, Wrench, RefreshCcw, RotateCcw, Power } from "lucide-react";

const StatusPill = ({ status }) => {
  const normalized = String(status || "unknown").toLowerCase();
  const color =
    normalized === "healthy" || normalized === "ok"
      ? "#00FF41"
      : normalized === "starting" || normalized === "stopping"
      ? "#FFD700"
      : "#FF3333";
  return (
    <span className="font-mono text-[10px] px-2 py-0.5 border" style={{ color, borderColor: color }}>
      {normalized.toUpperCase()}
    </span>
  );
};

const Card = ({ icon: Icon, title, children }) => (
  <div className="brutal-card p-5">
    <div className="flex items-center gap-2 mb-3">
      <Icon size={15} className="text-[#FF3333]" />
      <div className="overline">// {title}</div>
    </div>
    {children}
  </div>
);

export default function AdminOperations() {
  const [loading, setLoading] = useState(true);
  const [telemetry, setTelemetry] = useState(null);
  const [users, setUsers] = useState([]);
  const [payments, setPayments] = useState([]);
  const [audit, setAudit] = useState([]);
  const [notice, setNotice] = useState("");
  const [creating, setCreating] = useState(false);
  const [opsCapabilities, setOpsCapabilities] = useState({ host_controls_enabled: false, service_units: {} });
  const [busyOp, setBusyOp] = useState("");

  const [newUser, setNewUser] = useState({
    email: "",
    password: "",
    name: "",
    promo_code: "",
  });

  const refresh = async () => {
    setLoading(true);
    setNotice("");
    try {
      const [t, u, p, a] = await Promise.all([
        adminApi.telemetrySnapshot(),
        adminApi.listUsers(),
        adminApi.listPayments(),
        adminApi.listAuditLog(),
      ]);
      const caps = await adminApi.getOpsCapabilities();
      setTelemetry(t);
      setUsers(u || []);
      setPayments(p || []);
      setAudit(a || []);
      setOpsCapabilities(caps || { host_controls_enabled: false, service_units: {} });
    } catch (err) {
      setNotice(err?.response?.data?.detail || "Failed to load operations data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const startupSeq = telemetry?.startupSequence?.sequence_status || [];

  const pendingPayments = useMemo(
    () => (payments || []).filter((p) => ["awaiting_confirmation", "pending_manual_review", "awaiting_tx_hash"].includes(p.status)),
    [payments]
  );

  const operationsAudit = useMemo(() => {
    const opsActions = new Set([
      "restart_service",
      "restart_all_services",
      "reboot_server",
      "service_status_update",
      "service_heartbeat",
    ]);
    return (audit || [])
      .filter((e) => opsActions.has(String(e.action || "")))
      .slice(0, 100);
  }, [audit]);

  const createUser = async () => {
    if (!newUser.email || !newUser.password) {
      setNotice("Email and password are required");
      return;
    }
    setCreating(true);
    try {
      const res = await adminApi.createUser(newUser);
      if (res?.ok === false) {
        setNotice(res.message || "Create user endpoint unavailable");
      } else {
        setNotice(`User created: ${newUser.email}`);
        setNewUser({ email: "", password: "", name: "", promo_code: "" });
        await refresh();
      }
    } catch (err) {
      setNotice(err?.response?.data?.detail || "Failed to create user");
    } finally {
      setCreating(false);
    }
  };

  const setServiceStatus = async (serviceName, status) => {
    const res = await adminApi.updateServiceStatus(serviceName, status);
    if (res?.ok === false) {
      setNotice(`${serviceName}: ${res.message}`);
      return;
    }
    setNotice(`${serviceName} status -> ${status}`);
    await refresh();
  };

  const triggerHeartbeat = async (serviceName) => {
    const res = await adminApi.sendServiceHeartbeat(serviceName);
    if (res?.ok === false) {
      setNotice(`${serviceName}: ${res.message}`);
      return;
    }
    setNotice(`${serviceName} heartbeat sent`);
    await refresh();
  };

  const actPayment = async (id, action) => {
    const fn = action === "confirm" ? adminApi.confirmPayment : adminApi.rejectPayment;
    const res = await fn(id);
    if (res?.ok === false) {
      setNotice(res.message || `Unable to ${action} payment`);
      return;
    }
    setNotice(`Payment ${id.slice(0, 8)} ${action}ed`);
    await refresh();
  };

  const restartService = async (serviceName) => {
    if (!opsCapabilities?.host_controls_enabled) {
      setNotice("Host controls are disabled. Set ADMIN_ENABLE_HOST_CONTROLS=true.");
      return;
    }
    setBusyOp(`restart-${serviceName}`);
    try {
      const res = await adminApi.restartService(serviceName);
      if (!res?.ok) {
        setNotice(res?.result?.stderr || res?.message || `Failed to restart ${serviceName}`);
        return;
      }
      setNotice(`Restarted ${serviceName} successfully.`);
      await refresh();
    } finally {
      setBusyOp("");
    }
  };

  const restartAll = async () => {
    if (!opsCapabilities?.host_controls_enabled) {
      setNotice("Host controls are disabled. Set ADMIN_ENABLE_HOST_CONTROLS=true.");
      return;
    }
    if (!window.confirm("Restart ALL microservices now?")) return;
    setBusyOp("restart-all");
    try {
      const res = await adminApi.restartAllServices();
      if (!res?.ok) {
        setNotice(res?.message || "Some services failed to restart.");
      } else {
        setNotice("Restarted all services.");
      }
      await refresh();
    } finally {
      setBusyOp("");
    }
  };

  const rebootServer = async () => {
    if (!opsCapabilities?.host_controls_enabled) {
      setNotice("Host controls are disabled. Set ADMIN_ENABLE_HOST_CONTROLS=true.");
      return;
    }
    const yes = window.confirm("Reboot the PHYSICAL SERVER now? This disconnects all active sessions.");
    if (!yes) return;
    const phrase = window.prompt('Type REBOOT to confirm physical server reboot', '');
    if (phrase !== "REBOOT") return;
    setBusyOp("reboot-server");
    try {
      const res = await adminApi.rebootServer();
      if (!res?.ok) {
        setNotice(res?.result?.stderr || res?.message || "Reboot command failed.");
      } else {
        setNotice("Reboot command sent.");
      }
    } finally {
      setBusyOp("");
    }
  };

  if (loading) return <div className="font-mono text-zinc-500">loading operations<span className="blink">_</span></div>;

  return (
    <div className="space-y-6" data-testid="admin-operations">
      <div className="flex items-center justify-between">
        <div className="font-display font-bold text-xl">Admin Operations Center</div>
        <button className="brutal-btn !py-2 !px-3 flex items-center gap-2" onClick={refresh}>
          <RefreshCcw size={14} /> Refresh
        </button>
      </div>

      {notice && <div className="brutal-card p-3 font-mono text-xs text-zinc-300">{notice}</div>}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card icon={Activity} title="telemetry">
          <div className="font-mono text-xs text-zinc-400">Expected services: {telemetry?.summary?.expected ?? 6}</div>
          <div className="font-mono text-xs text-zinc-400">Registered: {telemetry?.summary?.registered ?? 0}</div>
          <div className="font-mono text-xs text-zinc-400">Unhealthy: {telemetry?.summary?.unhealthy ?? 0}</div>
          <div className="mt-2"><StatusPill status={telemetry?.summary?.allHealthy ? "healthy" : "degraded"} /></div>
        </Card>

        <Card icon={Server} title="service control">
          <div className="font-mono text-xs text-zinc-400">Control plane actions from orchestrator APIs.</div>
          <div className="font-mono text-[10px] text-zinc-500 mt-2">
            Host controls: {opsCapabilities?.host_controls_enabled ? "ENABLED" : "DISABLED (set ADMIN_ENABLE_HOST_CONTROLS=true)"}
          </div>
        </Card>

        <Card icon={Users} title="user admin">
          <div className="font-mono text-xs text-zinc-400">Users loaded: {users.length}</div>
          <div className="font-mono text-xs text-zinc-400">Admin creation + account lifecycle.</div>
        </Card>

        <Card icon={CreditCard} title="payments ops">
          <div className="font-mono text-xs text-zinc-400">Pending queue: {pendingPayments.length}</div>
          <div className="font-mono text-xs text-zinc-400">Manual confirm/reject where enabled.</div>
        </Card>
      </div>

      <Card icon={Server} title="services">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#222]">
                <th className="text-left overline py-2">service</th>
                <th className="text-left overline py-2">version</th>
                <th className="text-left overline py-2">alive</th>
                <th className="text-left overline py-2">health</th>
                <th className="text-left overline py-2">alive since</th>
                <th className="text-left overline py-2">actions</th>
              </tr>
            </thead>
            <tbody>
              {startupSeq.map((s) => {
                const versionChanged = s.last_version && s.version && s.last_version !== s.version;
                const alive = s.status === "healthy" || s.status === "starting";
                const ago = s.started_at ? (() => {
                  const ms = Date.now() - new Date(s.started_at).getTime();
                  const h = Math.floor(ms / 3600000);
                  const m = Math.floor((ms % 3600000) / 60000);
                  return `${h}h ${m}m`;
                })() : "—";
                return (
                <tr key={s.service_name} className="border-b border-[#222]">
                  <td className="font-mono text-xs py-2">{s.service_name}</td>
                  <td className="font-mono text-xs py-2">
                    {s.last_version && s.last_version !== s.version ? (
                      <span className="text-zinc-500 line-through mr-1">{s.last_version}</span>
                    ) : null}
                    <span className={versionChanged ? "text-[#00FF41]" : "text-zinc-300"}>{s.version || "—"}</span>
                  </td>
                  <td className="py-2">
                    <span className={`font-mono text-[10px] px-2 py-0.5 border ${alive ? "text-[#00FF41] border-[#00FF41]" : "text-[#FF3333] border-[#FF3333]"}`}>
                      {alive ? "UP" : "DOWN"}
                    </span>
                  </td>
                  <td className="py-2"><StatusPill status={s.status} /></td>
                  <td className="font-mono text-[10px] py-2 text-zinc-500">{ago}</td>
                  <td className="py-2">
                    <div className="flex gap-2 flex-wrap">
                      <button className="brutal-btn !py-1 !px-2 text-[10px]" onClick={() => triggerHeartbeat(s.service_name)}>heartbeat</button>
                      <button className="brutal-btn !py-1 !px-2 text-[10px]" onClick={() => setServiceStatus(s.service_name, "healthy")}>mark healthy</button>
                      <button className="brutal-btn !py-1 !px-2 text-[10px]" onClick={() => setServiceStatus(s.service_name, "stopping")}>mark stopping</button>
                      <button
                        className="brutal-btn !py-1 !px-2 text-[10px]"
                        onClick={() => restartService(s.service_name)}
                        disabled={busyOp === `restart-${s.service_name}`}
                      >
                        restart service
                      </button>
                    </div>
                  </td>
                </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card icon={Users} title="create user">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <input className="brutal-input" placeholder="Email" value={newUser.email} onChange={(e) => setNewUser({ ...newUser, email: e.target.value })} />
            <input className="brutal-input" placeholder="Password" type="password" value={newUser.password} onChange={(e) => setNewUser({ ...newUser, password: e.target.value })} />
            <input className="brutal-input" placeholder="Name (optional)" value={newUser.name} onChange={(e) => setNewUser({ ...newUser, name: e.target.value })} />
            <input className="brutal-input" placeholder="Promo code (optional)" value={newUser.promo_code} onChange={(e) => setNewUser({ ...newUser, promo_code: e.target.value })} />
          </div>
          <button className="brutal-btn brutal-btn-primary mt-3" onClick={createUser} disabled={creating}>{creating ? "CREATING..." : "CREATE USER"}</button>
        </Card>

        <Card icon={Wrench} title="system maintenance">
          <div className="font-mono text-xs text-zinc-400 mb-3">Use these checks before cutover and after deploy.</div>
          <div className="flex gap-2 flex-wrap">
            <button className="brutal-btn !py-2 !px-3 text-xs" onClick={refresh}>Run telemetry sweep</button>
            <button
              className="brutal-btn !py-2 !px-3 text-xs flex items-center gap-2"
              onClick={restartAll}
              disabled={busyOp === "restart-all" || !opsCapabilities?.host_controls_enabled}
            >
              <RotateCcw size={12} /> Restart All Services
            </button>
            <button
              className="brutal-btn !py-2 !px-3 text-xs flex items-center gap-2 !border-[#FF3333] !text-[#FF3333]"
              onClick={rebootServer}
              disabled={busyOp === "reboot-server" || !opsCapabilities?.host_controls_enabled}
            >
              <Power size={12} /> Reboot Physical Server
            </button>
          </div>
        </Card>
      </div>

      <Card icon={CreditCard} title="pending payments">
        <div className="space-y-2">
          {pendingPayments.length === 0 && <div className="font-mono text-xs text-zinc-500">No pending payments.</div>}
          {pendingPayments.map((p) => (
            <div key={p.id} className="flex flex-wrap items-center justify-between border border-[#222] px-3 py-2">
              <div className="font-mono text-xs text-zinc-300">
                <span className="text-white">{p.id?.slice(0, 8)}</span> · {p.plan_id} · {p.method} · ${p.amount_usd} · {p.status}
              </div>
              <div className="flex gap-2">
                <button className="brutal-btn !py-1 !px-2 text-[10px]" onClick={() => actPayment(p.id, "confirm")}>confirm</button>
                <button className="brutal-btn !py-1 !px-2 text-[10px]" onClick={() => actPayment(p.id, "reject")}>reject</button>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card icon={Wrench} title="operations audit">
        <div className="font-mono text-xs text-zinc-500 mb-3">Recent restart/reboot/service-control events (latest 100).</div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#222]">
                <th className="text-left overline py-2">time</th>
                <th className="text-left overline py-2">actor</th>
                <th className="text-left overline py-2">action</th>
                <th className="text-left overline py-2">target</th>
                <th className="text-left overline py-2">result</th>
              </tr>
            </thead>
            <tbody>
              {operationsAudit.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-4 font-mono text-xs text-zinc-500">No operations audit entries yet.</td>
                </tr>
              )}
              {operationsAudit.map((e) => (
                <tr key={e.id || `${e.at}-${e.action}`} className="border-b border-[#222]">
                  <td className="py-2 font-mono text-xs text-zinc-400">{String(e.at || "").slice(0, 19)}</td>
                  <td className="py-2 font-mono text-xs">{e.actor_email || "unknown"}</td>
                  <td className="py-2 font-mono text-xs text-zinc-300">{e.action || "—"}</td>
                  <td className="py-2 font-mono text-xs text-zinc-400">{e.target_service || e.unit || "—"}</td>
                  <td className="py-2">
                    <StatusPill status={e.ok === true ? "ok" : e.ok === false ? "fail" : "unknown"} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
