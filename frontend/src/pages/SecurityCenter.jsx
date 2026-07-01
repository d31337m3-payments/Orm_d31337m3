import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ShieldAlert, Bug, Lock, Mail, FileText } from "lucide-react";
import api from "@/lib/api";

function buildSecurityMailto(form) {
  const subject = encodeURIComponent(`[Security Report] ${form.reportType} - ${form.summary || "No summary"}`);
  const body = encodeURIComponent([
    "D31337m3 Security Report Submission",
    "",
    `Reporter Name: ${form.name || "N/A"}`,
    `Reporter Email: ${form.email || "N/A"}`,
    `Type: ${form.reportType}`,
    `Severity: ${form.severity}`,
    `Affected Flow: ${form.affectedFlow || "N/A"}`,
    `Known/Past Exploit Reference: ${form.knownExploit || "N/A"}`,
    `Summary: ${form.summary || "N/A"}`,
    "",
    "Reproduction Steps:",
    form.steps || "N/A",
    "",
    "Evidence / Proof:",
    form.proof || "N/A",
    "",
    `Disclosure Terms Accepted: ${form.accepted ? "YES" : "NO"}`,
  ].join("\n"));

  return `mailto:security@d31337m3.com?subject=${subject}&body=${body}`;
}

export default function SecurityCenter() {
  const [form, setForm] = useState({
    name: "",
    email: "",
    reportType: "security_breach",
    severity: "high",
    affectedFlow: "",
    knownExploit: "",
    summary: "",
    steps: "",
    proof: "",
    accepted: false,
  });
  const [sent, setSent] = useState(false);
  const [changelogs, setChangelogs] = useState(null);
  const [activeService, setActiveService] = useState(null);

  useEffect(() => {
    api.get("/api/public/changelogs")
      .then((res) => setChangelogs(res.data.changelogs))
      .catch(() => {});
  }, []);

  const canSubmit = useMemo(() => {
    return Boolean(
      form.email.trim() &&
      form.summary.trim() &&
      form.steps.trim() &&
      form.proof.trim() &&
      form.accepted
    );
  }, [form]);

  const onChange = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="min-h-screen bg-[#050505] text-white px-6 py-10">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <Link to="/" className="font-mono text-xs text-zinc-400 hover:text-white">← back to landing</Link>
          <Link to="/login" className="brutal-btn !py-2 !px-3 text-xs">login</Link>
        </div>

        <section className="brutal-card p-8 mb-6 border border-[#FF3333]/50">
          <div className="overline text-[#FF3333] mb-2">// security center</div>
          <h1 className="font-display font-black text-4xl mb-4">Report Security Breaches, Trust Voids, and Bugs</h1>
          <p className="font-mono text-zinc-300 leading-relaxed">
            D31337m3.com (pronounced <span className="text-white">delete me dot com</span>) is in active security-first refactor.
            Thank you for your patience while we harden and evolve this vision for privacy and reputation management.
          </p>
          <div className="mt-4 font-mono text-sm text-zinc-300">
            Security inbox: <a className="text-white hover:text-[#FF3333]" href="mailto:security@d31337m3.com">security@d31337m3.com</a>
            <span className="text-zinc-500"> (filtered and forwarded to admins/security team members)</span>
          </div>
          <div className="mt-2 font-mono text-sm text-zinc-300">
            General support: <a className="text-white hover:text-[#FF3333]" href="mailto:support@d31337m3.com">support@d31337m3.com</a>
          </div>
        </section>

        <section className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="brutal-card p-5">
            <ShieldAlert className="text-[#FF3333] mb-2" size={18} />
            <div className="font-display font-black text-xl mb-2">Security Measures In Place</div>
            <ul className="font-mono text-xs text-zinc-400 space-y-1">
              <li>JWT auth and verification middleware</li>
              <li>Infisical-first secrets strategy</li>
              <li>Public telemetry redaction controls</li>
              <li>Service isolation and operational health gates</li>
            </ul>
          </div>
          <div className="brutal-card p-5">
            <Bug className="text-[#FFD700] mb-2" size={18} />
            <div className="font-display font-black text-xl mb-2">What To Report</div>
            <ul className="font-mono text-xs text-zinc-400 space-y-1">
              <li>Security breaches</li>
              <li>Trust voidances</li>
              <li>Broken flows / logic abuse</li>
              <li>Known and past patched exploit regressions</li>
            </ul>
          </div>
          <div className="brutal-card p-5">
            <Lock className="text-[#00FF41] mb-2" size={18} />
            <div className="font-display font-black text-xl mb-2">Proposed Bounty Program</div>
            <p className="font-mono text-xs text-zinc-400 leading-relaxed">
              We reserve <span className="text-white">$1000</span> in a dedicated reward account. A validated and authentic exploit report with proof and responsible disclosure is eligible for:
            </p>
            <ul className="font-mono text-xs text-zinc-400 mt-2 space-y-1">
              <li>$1000 reward payout</li>
              <li>6-month Pro subscription free</li>
            </ul>
          </div>
        </section>

        <section className="brutal-card p-8 mb-6">
          <div className="overline mb-2">// curte</div>
          <h2 className="font-display font-black text-2xl mb-2">CURTE Reporting Values</h2>
          <div className="font-mono text-xs text-zinc-400 grid grid-cols-1 md:grid-cols-2 gap-2">
            <div>C - Clear report scope and impact statement</div>
            <div>U - Urgent risk classification</div>
            <div>R - Reproducible evidence and steps</div>
            <div>T - Traceable logs, timestamps, and vectors</div>
            <div>E - Ethical disclosure to security@d31337m3.com</div>
          </div>
        </section>

        <section className="brutal-card p-8">
          <div className="overline mb-2">// submit exploit / bug report</div>
          <h2 className="font-display font-black text-2xl mb-6">Security Report Form</h2>
          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              if (!canSubmit) return;
              window.location.href = buildSecurityMailto(form);
              setSent(true);
            }}
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div className="overline mb-1">name</div>
                <input className="brutal-input" value={form.name} onChange={(e) => onChange("name", e.target.value)} />
              </div>
              <div>
                <div className="overline mb-1">email *</div>
                <input type="email" className="brutal-input" required value={form.email} onChange={(e) => onChange("email", e.target.value)} />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <div className="overline mb-1">report type *</div>
                <select className="brutal-input" value={form.reportType} onChange={(e) => onChange("reportType", e.target.value)}>
                  <option value="security_breach">Security Breach</option>
                  <option value="trust_voidance">Trust Voidance</option>
                  <option value="bug">Bug</option>
                  <option value="broken_flow">Broken Flow</option>
                  <option value="exploit">Exploit</option>
                </select>
              </div>
              <div>
                <div className="overline mb-1">severity *</div>
                <select className="brutal-input" value={form.severity} onChange={(e) => onChange("severity", e.target.value)}>
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>
              <div>
                <div className="overline mb-1">affected flow</div>
                <input className="brutal-input" value={form.affectedFlow} onChange={(e) => onChange("affectedFlow", e.target.value)} placeholder="login, register, billing, docs, etc." />
              </div>
            </div>

            <div>
              <div className="overline mb-1">known or past patched exploit reference</div>
              <input className="brutal-input" value={form.knownExploit} onChange={(e) => onChange("knownExploit", e.target.value)} placeholder="CVE, internal ticket, prior patch ID" />
            </div>

            <div>
              <div className="overline mb-1">summary *</div>
              <input className="brutal-input" required value={form.summary} onChange={(e) => onChange("summary", e.target.value)} />
            </div>

            <div>
              <div className="overline mb-1">reproduction steps *</div>
              <textarea className="brutal-input min-h-[120px]" required value={form.steps} onChange={(e) => onChange("steps", e.target.value)} />
            </div>

            <div>
              <div className="overline mb-1">proof / evidence *</div>
              <textarea className="brutal-input min-h-[120px]" required value={form.proof} onChange={(e) => onChange("proof", e.target.value)} placeholder="POC details, logs, payloads, screenshots, traces" />
            </div>

            <label className="flex items-center gap-2 font-mono text-xs text-zinc-300">
              <input type="checkbox" checked={form.accepted} onChange={(e) => onChange("accepted", e.target.checked)} />
              I confirm this report is authentic and shared under responsible disclosure.
            </label>

            <button type="submit" disabled={!canSubmit} className="brutal-btn brutal-btn-primary flex items-center gap-2">
              <Mail size={14} /> Submit to security@d31337m3.com
            </button>

            {sent && (
              <div className="font-mono text-xs text-[#00FF41]">
                Draft opened in your mail client. If needed, send directly to security@d31337m3.com and cc support@d31337m3.com.
              </div>
            )}
          </form>
        </section>

        <section className="brutal-card p-8 mt-6">
          <div className="overline mb-2">// changelogs</div>
          <h2 className="font-display font-black text-2xl mb-2">Microservice Changelog Audit</h2>
          <p className="font-mono text-xs text-zinc-400 mb-6">
            Public changelog for all microservices powering the d31337m3 platform.
            Select a service to view its version history.
          </p>

          <div className="flex flex-wrap gap-2 mb-6">
            {changelogs && Object.keys(changelogs).sort().map((svc) => (
              <button
                key={svc}
                onClick={() => setActiveService(activeService === svc ? null : svc)}
                className={`font-mono text-xs px-3 py-1.5 border transition-colors ${
                  activeService === svc
                    ? "border-[#00FF41] text-[#00FF41] bg-[#00FF41]/10"
                    : "border-zinc-700 text-zinc-400 hover:border-zinc-500"
                }`}
              >
                {svc}
              </button>
            ))}
            {!changelogs && (
              <span className="font-mono text-xs text-zinc-600">loading...</span>
            )}
          </div>

          {activeService && changelogs && (() => {
            const lines = changelogs[activeService].split("\n");
            return (
              <div className="font-mono text-xs text-zinc-300 bg-black/50 p-4 rounded max-h-[600px] overflow-y-auto whitespace-pre-wrap">
                {lines.map((line, i) => {
                  const isHeading = line.startsWith("# ");
                  const isVersion = /^##\s/.test(line);
                  const isBullet = line.startsWith("- ") || line.startsWith("  -");
                  return (
                    <div
                      key={i}
                      className={`${
                        isHeading ? "text-white font-bold text-sm mt-2 mb-1" : ""
                      }${isVersion ? "text-[#00FF41] font-bold text-xs mt-3 mb-1" : ""}${
                        isBullet ? "text-zinc-400 pl-4" : ""
                      }${!isHeading && !isVersion && !isBullet ? "text-zinc-500" : ""}`}
                    >
                      {line || "\u00A0"}
                    </div>
                  );
                })}
              </div>
            );
          })()}
        </section>
      </div>
    </div>
  );
}
