import React, { useEffect, useState } from "react";
import DashboardLayout from "@/components/DashboardLayout";
import SignaturePad from "@/components/SignaturePad";
import api from "@/lib/api";
import { motion } from "framer-motion";
import { FileText, Download, Trash2, PenLine, FileSignature, Eye } from "lucide-react";

const TEMPLATE_ICONS = {
  dmca_takedown: "⚖",
  cease_and_desist: "⛔",
  privacy_removal_request: "🔒",
  right_to_be_forgotten: "🌐",
};

export default function Documents() {
  const [tab, setTab] = useState("documents");
  const [templates, setTemplates] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [findings, setFindings] = useState([]);
  const [signature, setSignature] = useState(null);
  const [sigName, setSigName] = useState("");
  const [profile, setProfile] = useState({ country: "CA", state: "ON", address: "", phone: "", name: "" });
  const [countries, setCountries] = useState({});
  const [viewing, setViewing] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [genForm, setGenForm] = useState({ template_id: "", finding_id: "", recipient_broker: "", recipient_address: "" });

  const load = async () => {
    const [t, d, f, s, p, c] = await Promise.all([
      api.get("/documents/templates"),
      api.get("/documents"),
      api.get("/findings"),
      api.get("/signature"),
      api.get("/profile"),
      api.get("/countries"),
    ]);
    setTemplates(t.data.templates);
    setDocuments(d.data.documents);
    setFindings(f.data.findings);
    setSignature(s.data.signature);
    setProfile(p.data.profile);
    setCountries(c.data.countries);
    setSigName(s.data.signature?.full_name || p.data.profile?.name || "");
  };
  useEffect(() => { load(); }, []);

  // If user clicked "Legal" on a finding, jump straight to Generate tab pre-filled
  useEffect(() => {
    const pending = sessionStorage.getItem("d31337m3_pending_finding");
    if (pending) {
      try {
        const { finding_id, broker } = JSON.parse(pending);
        setGenForm((g) => ({ ...g, finding_id, recipient_broker: broker || "" }));
        setTab("generate");
      } catch (e) { /* ignore */ }
      sessionStorage.removeItem("d31337m3_pending_finding");
    }
  }, []);

  const saveSignature = async (dataUrl) => {
    await api.post("/signature", { data_url: dataUrl, full_name: sigName });
    load();
    setTab("documents");
  };

  const saveProfile = async () => {
    await api.put("/profile", profile);
    alert("Profile updated.");
    load();
  };

  const generate = async () => {
    if (!genForm.template_id) return;
    setGenerating(true);
    try {
      const r = await api.post("/documents/generate", genForm);
      setViewing(r.data.document);
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to generate");
    } finally { setGenerating(false); }
  };

  const sign = async (id) => {
    try {
      const r = await api.post("/documents/sign", { document_id: id });
      const fresh = await api.get(`/documents/${id}`);
      setViewing(fresh.data.document);
      load();
      const d = r.data.dispatch || {};
      if (d.delivered && d.broker_email) {
        alert(`✓ Signed & dispatched to ${d.broker_email}`);
      } else if (d.form_url) {
        alert(`✓ Signed. This broker requires manual submission via their opt-out form:\n${d.form_url}`);
      } else {
        alert("✓ Document signed.");
      }
    } catch (e) { alert(e.response?.data?.detail || "Failed"); }
  };

  const del = async (id) => {
    if (!window.confirm("Delete document?")) return;
    await api.delete(`/documents/${id}`);
    load();
  };

  const downloadTxt = (doc) => {
    const blob = new Blob([doc.body], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `${doc.title.replace(/[^a-z0-9]/gi, "_")}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const printDoc = (doc) => {
    const w = window.open("", "_blank");
    if (!w) return;
    const sigHtml = doc.signature_image
      ? `<div style="margin-top:30px"><img src="${doc.signature_image}" style="max-height:80px;background:#fff;padding:6px;border:1px solid #ccc"/><div style="font-family:monospace;font-size:12px;color:#666;margin-top:6px">Electronically signed by ${doc.signed_name} on ${doc.signed_at}</div></div>`
      : "";
    w.document.write(`<html><head><title>${doc.title}</title><style>body{font-family:Georgia,serif;max-width:780px;margin:40px auto;padding:0 20px;line-height:1.6;color:#111}pre{white-space:pre-wrap;font-family:Georgia,serif;font-size:14px}</style></head><body><h1>${doc.title}</h1><pre>${doc.body}</pre>${sigHtml}</body></html>`);
    w.document.close();
    w.focus();
    setTimeout(() => w.print(), 300);
  };

  return (
    <DashboardLayout title="Legal Documents — North America 🇨🇦 🇺🇸 🇲🇽">
      <div className="brutal-card p-4 mb-6 border-[#FF3333]/40 bg-[#1a0808]/30">
        <div className="font-mono text-xs text-zinc-300">
          <span className="text-[#FF3333] font-bold">// JURISDICTION:</span> Legal document services are available exclusively for residents of
          <span className="text-white"> Canada (PIPEDA/Quebec Law 25)</span>,
          <span className="text-white"> United States (CCPA/CPRA/DMCA)</span>, and
          <span className="text-white"> México (LFPDPPP)</span>.
          Documents are e-signed under ESIGN Act / UECA / LFFEA.
        </div>
      </div>

      <div className="flex gap-2 mb-6" data-testid="docs-tabs">
        {[["documents","My Documents"],["generate","Generate New"],["signature","E-Signature"],["profile","Profile"]].map(([k,l]) => (
          <button key={k} onClick={()=>setTab(k)} data-testid={`docs-tab-${k}`}
            className={`font-mono text-xs px-4 py-2 border ${tab===k ? "border-white text-white" : "border-[#222] text-zinc-500 hover:text-white"}`}>
            {l.toUpperCase()}
          </button>
        ))}
      </div>

      {tab === "documents" && (
        <div className="brutal-card p-6" data-testid="documents-panel">
          {documents.length === 0 ? (
            <div className="font-mono text-zinc-500 py-6">No documents yet. Go to <button onClick={()=>setTab("generate")} className="text-[#FF3333]">Generate New →</button> to create your first legal notice.</div>
          ) : (
            <table className="w-full">
              <thead><tr className="border-b border-[#222]">
                {["Title","Recipient","Country","Status","Created","Actions"].map(h=><th key={h} className="overline text-left py-2">{h}</th>)}
              </tr></thead>
              <tbody>
                {documents.map(d => (
                  <tr key={d.id} className="border-b border-[#222] hover:bg-[#0a0a0a]" data-testid={`document-row-${d.id}`}>
                    <td className="py-3 font-mono text-sm">{TEMPLATE_ICONS[d.template_id]} {d.title}</td>
                    <td className="py-3 font-mono text-xs text-zinc-400">{d.recipient_broker}</td>
                    <td className="py-3 font-mono text-xs">{d.country}</td>
                    <td className="py-3 font-mono text-xs">
                      {d.status === "signed"
                        ? <span className="text-[#00FF41]">SIGNED</span>
                        : <span className="text-[#FFD700]">DRAFT</span>}
                    </td>
                    <td className="py-3 font-mono text-xs text-zinc-500">{d.created_at?.slice(0,10)}</td>
                    <td className="py-3 flex gap-3">
                      <button onClick={()=>setViewing(d)} data-testid={`view-doc-${d.id}`} className="text-zinc-400 hover:text-white" title="View"><Eye size={14}/></button>
                      {d.status !== "signed" && (
                        <button onClick={()=>sign(d.id)} data-testid={`sign-doc-${d.id}`} className="text-[#00FF41] hover:text-white" title="Sign"><FileSignature size={14}/></button>
                      )}
                      <button onClick={()=>downloadTxt(d)} data-testid={`download-doc-${d.id}`} className="text-zinc-400 hover:text-white" title="Download"><Download size={14}/></button>
                      <button onClick={()=>del(d.id)} data-testid={`delete-doc-${d.id}`} className="text-[#FF3333] hover:text-white" title="Delete"><Trash2 size={14}/></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {tab === "generate" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6" data-testid="generate-panel">
          <div className="brutal-card p-6">
            <div className="overline mb-3">// pick a template</div>
            <div className="space-y-3">
              {templates.map(t => (
                <motion.button
                  whileHover={{ x: 4 }}
                  key={t.id}
                  onClick={() => t.available && setGenForm({...genForm, template_id: t.id})}
                  disabled={!t.available}
                  data-testid={`template-${t.id}`}
                  className={`w-full text-left border p-4 transition-all ${genForm.template_id===t.id ? "border-[#FF3333] bg-[#1a0808]" : t.available ? "border-[#222] hover:border-white" : "border-[#222] opacity-40 cursor-not-allowed"}`}
                >
                  <div className="font-display font-bold text-lg flex items-center gap-2">
                    <span className="text-2xl">{TEMPLATE_ICONS[t.id]}</span>{t.title}
                  </div>
                  <div className="font-mono text-xs text-zinc-400 mt-1">{t.summary}</div>
                  <div className="font-mono text-[10px] tracking-widest text-zinc-500 mt-2">
                    JURISDICTIONS: {t.jurisdictions.join(" · ")}
                    {!t.available && <span className="text-[#FF3333]"> · NOT AVAILABLE FOR YOUR COUNTRY</span>}
                  </div>
                </motion.button>
              ))}
            </div>
          </div>

          <div className="brutal-card p-6">
            <div className="overline mb-3">// document details</div>
            <div className="space-y-3">
              <div>
                <div className="overline mb-1">link to finding (optional)</div>
                <select data-testid="gen-finding" value={genForm.finding_id} onChange={(e)=>setGenForm({...genForm, finding_id: e.target.value})} className="brutal-input">
                  <option value="">— none —</option>
                  {findings.filter(f=>f.status==="active").map(f => (
                    <option key={f.id} value={f.id}>{f.broker} — {f.keyword_value}</option>
                  ))}
                </select>
              </div>
              <div>
                <div className="overline mb-1">recipient (broker / company name)</div>
                <input data-testid="gen-recipient" value={genForm.recipient_broker} onChange={(e)=>setGenForm({...genForm, recipient_broker: e.target.value})} placeholder="e.g. Spokeo Inc." className="brutal-input" />
              </div>
              <div>
                <div className="overline mb-1">recipient address</div>
                <input data-testid="gen-recipient-addr" value={genForm.recipient_address} onChange={(e)=>setGenForm({...genForm, recipient_address: e.target.value})} placeholder="123 Privacy Way, City, State, ZIP" className="brutal-input" />
              </div>
              <button onClick={generate} disabled={!genForm.template_id || generating} data-testid="generate-doc-btn" className="brutal-btn brutal-btn-primary w-full flex items-center gap-2 justify-center">
                <FileText size={14}/>{generating ? "Generating..." : "Generate Document"}
              </button>
              {!signature && (
                <div className="font-mono text-xs text-[#FFD700] mt-2">⚠ Heads up: you&apos;ll need an e-signature on file to sign generated documents. <button onClick={()=>setTab("signature")} className="underline">Set one up →</button></div>
              )}
            </div>
          </div>
        </div>
      )}

      {tab === "signature" && (
        <div className="space-y-6">
          <SignaturePad onSave={saveSignature} fullName={sigName} setFullName={setSigName} existing={signature} />
        </div>
      )}

      {tab === "profile" && (
        <div className="brutal-card p-6 max-w-2xl" data-testid="profile-panel">
          <div className="overline mb-4">// personal info (used in legal documents)</div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <div className="overline mb-1">full legal name</div>
              <input data-testid="profile-name" value={profile.name || ""} onChange={(e)=>setProfile({...profile, name: e.target.value})} className="brutal-input" />
            </div>
            <div>
              <div className="overline mb-1">phone</div>
              <input data-testid="profile-phone" value={profile.phone || ""} onChange={(e)=>setProfile({...profile, phone: e.target.value})} className="brutal-input" />
            </div>
            <div className="md:col-span-2">
              <div className="overline mb-1">street address</div>
              <input data-testid="profile-address" value={profile.address || ""} onChange={(e)=>setProfile({...profile, address: e.target.value})} className="brutal-input" />
            </div>
            <div>
              <div className="overline mb-1">country</div>
              <select data-testid="profile-country" value={profile.country || "CA"} onChange={(e)=>setProfile({...profile, country: e.target.value, state: ""})} className="brutal-input">
                {Object.entries(countries).map(([code, c]) => <option key={code} value={code}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <div className="overline mb-1">state / province</div>
              <select data-testid="profile-state" value={profile.state || ""} onChange={(e)=>setProfile({...profile, state: e.target.value})} className="brutal-input">
                <option value="">—</option>
                {(countries[profile.country]?.states || []).map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>
          <div className="mt-3 font-mono text-xs text-zinc-500">
            Privacy law applicable to your jurisdiction: <span className="text-white">{countries[profile.country]?.privacy_law}</span>
          </div>
          <button onClick={saveProfile} data-testid="profile-save" className="brutal-btn brutal-btn-primary mt-5 flex items-center gap-2"><PenLine size={14}/>Save Profile</button>
        </div>
      )}

      {/* Viewer modal */}
      {viewing && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4" onClick={()=>setViewing(null)} data-testid="doc-viewer">
          <div onClick={(e)=>e.stopPropagation()} className="brutal-card max-w-3xl w-full max-h-[90vh] overflow-y-auto p-8 bg-[#0a0a0a]">
            <div className="flex justify-between items-start mb-4">
              <div>
                <div className="overline mb-1">// legal document</div>
                <h2 className="font-display font-black text-2xl">{viewing.title}</h2>
                <div className="font-mono text-xs text-zinc-500 mt-1">{viewing.country} · {viewing.status === "signed" ? <span className="text-[#00FF41]">SIGNED</span> : <span className="text-[#FFD700]">DRAFT</span>}</div>
              </div>
              <button onClick={()=>setViewing(null)} className="text-zinc-500 hover:text-white">✕</button>
            </div>
            <pre className="font-mono text-xs text-zinc-300 whitespace-pre-wrap border border-[#222] p-5 bg-black mb-4">{viewing.body}</pre>
            {viewing.signature_image && (
              <div className="border border-[#222] p-3 bg-[#0a0a0a]">
                <div className="overline mb-2">// affixed signature</div>
                <img src={viewing.signature_image} alt="signature" className="max-h-20 bg-white p-2 inline-block" />
                <div className="font-mono text-xs text-zinc-500 mt-2">› {viewing.signed_name} · {viewing.signed_at?.slice(0,16)}</div>
              </div>
            )}
            <div className="flex gap-3 mt-5">
              {viewing.status !== "signed" && <button onClick={()=>sign(viewing.id)} data-testid="viewer-sign-btn" className="brutal-btn brutal-btn-primary">Sign Now</button>}
              <button onClick={()=>printDoc(viewing)} data-testid="viewer-print-btn" className="brutal-btn">Print / Save PDF</button>
              <button onClick={()=>downloadTxt(viewing)} data-testid="viewer-download-btn" className="brutal-btn">Download .txt</button>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
