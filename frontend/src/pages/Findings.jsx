import React, { useEffect, useState } from "react";
import DashboardLayout from "@/components/DashboardLayout";
import api from "@/lib/api";
import { useNavigate } from "react-router-dom";
import { FileSignature } from "lucide-react";

const StatusBadge = ({ status }) => {
  const map = {
    active: { color: "#FF3333", label: "ACTIVE" },
    pending_removal: { color: "#FFD700", label: "PENDING" },
    removed: { color: "#00FF41", label: "REMOVED" },
  };
  const m = map[status] || { color: "#71717a", label: (status || "").toUpperCase() };
  return <span className="font-mono text-xs px-2 py-1 border" style={{ color: m.color, borderColor: m.color }}>{m.label}</span>;
};

export default function Findings() {
  const [findings, setFindings] = useState([]);
  const [filter, setFilter] = useState("all");
  const nav = useNavigate();

  const load = async () => {
    const r = await api.get("/findings");
    setFindings(r.data.findings);
  };
  useEffect(() => { load(); }, []);

  const requestRemoval = async (id) => {
    await api.post("/findings/removal-request", { finding_id: id });
    load();
  };

  const generateLegal = (f) => {
    // jump to documents page with finding hinted via session (lightweight)
    sessionStorage.setItem("d31337m3_pending_finding", JSON.stringify({ finding_id: f.id, broker: f.broker }));
    nav("/documents");
  };

  const filtered = findings.filter(f => filter === "all" ? true : f.status === filter);

  return (
    <DashboardLayout title="Data Broker Findings">
      <div className="flex gap-2 mb-6 flex-wrap" data-testid="findings-filters">
        {[
          ["all","All"],["active","Active"],["pending_removal","Pending"],["removed","Removed"]
        ].map(([k,l]) => (
          <button key={k} onClick={()=>setFilter(k)} data-testid={`filter-${k}`}
            className={`font-mono text-xs px-4 py-2 border ${filter===k ? "border-white text-white" : "border-[#222] text-zinc-500 hover:text-white"}`}>
            {l.toUpperCase()}
          </button>
        ))}
      </div>

      <div className="brutal-card p-6">
        {filtered.length === 0 ? (
          <div className="font-mono text-zinc-500 py-6" data-testid="empty-findings">No findings match this filter.</div>
        ) : (
          <table className="w-full" data-testid="findings-table">
            <thead><tr className="border-b border-[#222]">
              {["Broker","Keyword","Data Exposed","Severity","Status","Discovered","Actions"].map(h=><th key={h} className="overline text-left py-2">{h}</th>)}
            </tr></thead>
            <tbody>
              {filtered.map(f => (
                <tr key={f.id} className="border-b border-[#222] hover:bg-[#0a0a0a]" data-testid={`finding-row-${f.id}`}>
                  <td className="py-3 font-mono text-sm">
                    <a href={f.url} target="_blank" rel="noopener noreferrer" className="hover:text-[#FF3333]">{f.broker}</a>
                  </td>
                  <td className="py-3 font-mono text-xs text-zinc-400">{f.keyword_value}</td>
                  <td className="py-3 font-mono text-xs text-zinc-500">{(f.data_found || []).join(", ")}</td>
                  <td className={`py-3 font-mono text-xs severity-${f.severity}`}>{(f.severity || "").toUpperCase()}</td>
                  <td className="py-3"><StatusBadge status={f.status} /></td>
                  <td className="py-3 font-mono text-xs text-zinc-500">{f.discovered_at?.slice(0,10)}</td>
                  <td className="py-3 flex gap-3">
                    {f.status === "active" && (
                      <>
                        <button onClick={()=>requestRemoval(f.id)} data-testid={`request-removal-${f.id}`} className="font-mono text-xs text-[#FF3333] hover:text-white">REMOVAL</button>
                        <button onClick={()=>generateLegal(f)} data-testid={`legal-${f.id}`} className="font-mono text-xs text-[#FFD700] hover:text-white flex items-center gap-1"><FileSignature size={12}/>LEGAL</button>
                      </>
                    )}
                    {f.status !== "active" && <span className="font-mono text-xs text-zinc-600">—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </DashboardLayout>
  );
}
