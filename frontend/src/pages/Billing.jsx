import React, { useEffect, useState } from "react";
import DashboardLayout from "@/components/DashboardLayout";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Copy, CheckCircle2 } from "lucide-react";

export default function Billing() {
  const { user, refresh } = useAuth();
  const [plans, setPlans] = useState([]);
  const [payments, setPayments] = useState([]);
  const [selPlan, setSelPlan] = useState("pro");
  const [method, setMethod] = useState("crypto");
  const [network, setNetwork] = useState("base");
  const [txHash, setTxHash] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState("");

  const load = async () => {
    const [p, pay] = await Promise.all([api.get("/plans"), api.get("/payments")]);
    setPlans(p.data.plans);
    setPayments(pay.data.payments);
  };
  useEffect(() => { load(); }, []);

  const subscribe = async (e) => {
    e.preventDefault();
    setBusy(true); setResult(null);
    try {
      const body = { plan_id: selPlan, payment_method: method };
      if (method === "crypto" && txHash) {
        body.network = network;
        body.tx_hash = txHash;
      }
      const r = await api.post("/subscribe", body);
      setResult(r.data);
      load(); refresh();
    } catch (e) { setResult({ error: e.response?.data?.detail || "Failed" }); }
    finally { setBusy(false); }
  };

  const copy = (text, key) => {
    navigator.clipboard.writeText(text);
    setCopied(key); setTimeout(()=>setCopied(""), 1500);
  };

  return (
    <DashboardLayout title="Billing & Subscription">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {plans.map(p => (
          <div key={p.id} data-testid={`billing-plan-${p.id}`}
               className={`brutal-card p-6 cursor-pointer ${selPlan === p.id ? "border-[#FF3333]" : ""}`}
               onClick={()=>setSelPlan(p.id)}>
            <div className="overline mb-2">// {p.id}</div>
            <div className="font-display font-black text-2xl mb-1">{p.name}</div>
            <div className="font-display font-black text-4xl mb-4">${p.price_usd}<span className="text-sm text-zinc-500">/mo</span></div>
            <ul className="space-y-1">
              {p.features.map(f => <li key={f} className="font-mono text-xs text-zinc-400">› {f}</li>)}
            </ul>
            {user?.plan_id === p.id && user?.subscription_status === "active" && (
              <div className="mt-3 font-mono text-xs text-[#00FF41]">› ACTIVE</div>
            )}
          </div>
        ))}
      </div>

      <div className="brutal-card p-8 mb-6">
        <div className="overline mb-3">// checkout</div>
        <h2 className="font-display font-bold text-2xl mb-6">Subscribe to {plans.find(p=>p.id===selPlan)?.name} (${plans.find(p=>p.id===selPlan)?.price_usd}/mo)</h2>

        <form onSubmit={subscribe} className="space-y-5" data-testid="checkout-form">
          <div>
            <div className="overline mb-2">payment method</div>
            <div className="grid grid-cols-3 gap-3">
              {[
                ["crypto","Crypto (USDC)"],
                ["interac","Interac e-Transfer"],
                ["paypal","PayPal"],
              ].map(([k,l]) => (
                <button key={k} type="button" onClick={()=>setMethod(k)} data-testid={`method-${k}`}
                  className={`border p-4 text-left ${method===k ? "border-[#FF3333] bg-[#1a0808]" : "border-[#222] hover:border-white"}`}>
                  <div className="font-display font-bold">{l}</div>
                  <div className="font-mono text-xs text-zinc-500 mt-1">{k === "crypto" ? "ETH / Polygon / Base" : k === "interac" ? "Canadian Email Transfer" : "Card or PayPal balance"}</div>
                </button>
              ))}
            </div>
          </div>

          {method === "crypto" && (
            <div className="space-y-3" data-testid="crypto-fields">
              <div>
                <div className="overline mb-2">network</div>
                <div className="grid grid-cols-3 gap-3">
                  {["base","polygon","ethereum"].map(n => (
                    <button key={n} type="button" onClick={()=>setNetwork(n)} data-testid={`network-${n}`}
                      className={`border p-3 font-mono text-sm uppercase ${network===n ? "border-[#FF3333] text-white" : "border-[#222] text-zinc-500 hover:text-white"}`}>
                      {n}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <div className="overline mb-2">transaction hash (after sending USDC)</div>
                <input data-testid="tx-hash-input" value={txHash} onChange={(e)=>setTxHash(e.target.value)} placeholder="0x..." className="brutal-input" />
                <div className="font-mono text-xs text-zinc-500 mt-2">Leave blank to first get the wallet address & instructions.</div>
              </div>
            </div>
          )}

          <button type="submit" disabled={busy} data-testid="subscribe-submit" className="brutal-btn brutal-btn-primary">
            {busy ? "Processing..." : method === "crypto" && !txHash ? "Get Wallet Address" : "Submit Payment"}
          </button>
        </form>

        {result && (
          <div className="mt-6 border border-[#222] p-5 bg-[#0a0a0a]" data-testid="payment-result">
            {result.error && <div className="font-mono text-[#FF3333]">› {result.error}</div>}
            {result.status === "confirmed" && <div className="font-mono text-[#00FF41]">✓ Payment confirmed! Your subscription is now active.</div>}
            {result.status === "pending_manual_review" && <div className="font-mono text-[#FFD700]">⚠ {result.message}</div>}
            {result.status === "paypal_unavailable" && <div className="font-mono text-[#FFD700]">⚠ {result.message}</div>}
            {result.instructions && (
              <div className="mt-4 space-y-3">
                <div className="overline">// instructions</div>
                {result.instructions.recipient_email && (
                  <div>
                    <div className="font-mono text-xs text-zinc-500">Send Interac e-Transfer to:</div>
                    <div className="flex items-center gap-2 mt-1">
                      <code className="font-mono text-white text-lg">{result.instructions.recipient_email}</code>
                      <button type="button" onClick={()=>copy(result.instructions.recipient_email,"email")} data-testid="copy-email">
                        {copied==="email" ? <CheckCircle2 size={14} className="text-[#00FF41]"/> : <Copy size={14} className="text-zinc-400 hover:text-white"/>}
                      </button>
                    </div>
                    <div className="font-mono text-xs text-zinc-500 mt-2">Amount: <span className="text-white">${result.instructions.amount_usd} USD</span> {result.instructions.amount_cad_estimate && <span className="text-zinc-500">(≈ ${result.instructions.amount_cad_estimate} CAD)</span>}</div>
                    <div className="font-mono text-xs text-zinc-500">Note / Memo: <span className="text-white">{result.instructions.note}</span></div>
                    {result.instructions.auto_deposit && (
                      <div className="mt-3 border-l-2 border-[#00FF41] pl-3 py-1 bg-[#0a1f0a]/30">
                        <div className="font-mono text-xs text-[#00FF41] font-bold">✓ AUTO-DEPOSIT ENABLED</div>
                        <div className="font-mono text-xs text-zinc-400 mt-1">No security question required. Funds settle automatically.</div>
                      </div>
                    )}
                    {result.instructions.instructions && (
                      <pre className="mt-3 font-mono text-xs text-zinc-300 whitespace-pre-wrap border border-[#222] p-3 bg-black">{result.instructions.instructions}</pre>
                    )}
                  </div>
                )}
                {result.instructions.wallet && (
                  <div>
                    <div className="font-mono text-xs text-zinc-500">Send {result.instructions.amount_usdc} USDC to:</div>
                    <div className="flex items-center gap-2 mt-1">
                      <code className="font-mono text-white text-sm break-all">{result.instructions.wallet}</code>
                      <button type="button" onClick={()=>copy(result.instructions.wallet,"wallet")} data-testid="copy-wallet">
                        {copied==="wallet" ? <CheckCircle2 size={14} className="text-[#00FF41]"/> : <Copy size={14} className="text-zinc-400 hover:text-white"/>}
                      </button>
                    </div>
                    <div className="font-mono text-xs text-zinc-500 mt-2">Networks: <span className="text-white">{result.instructions.networks?.join(", ")}</span></div>
                    <div className="font-mono text-xs text-zinc-500">Memo: <span className="text-white">{result.instructions.memo}</span></div>
                    <div className="font-mono text-xs text-[#FFD700] mt-2">After sending, paste the tx hash above and resubmit.</div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="brutal-card p-6">
        <div className="overline mb-3">// payment history</div>
        {payments.length === 0 ? (
          <div className="font-mono text-zinc-500 py-4">No payments yet.</div>
        ) : (
          <table className="w-full" data-testid="payments-table">
            <thead><tr className="border-b border-[#222]">
              {["Date","Plan","Method","Amount","Status"].map(h=><th key={h} className="overline text-left py-2">{h}</th>)}
            </tr></thead>
            <tbody>
              {payments.map(p => (
                <tr key={p.id} className="border-b border-[#222]">
                  <td className="py-3 font-mono text-xs text-zinc-500">{p.created_at?.slice(0,10)}</td>
                  <td className="py-3 font-mono text-sm">{p.plan_id}</td>
                  <td className="py-3 font-mono text-xs text-zinc-400">{p.method}</td>
                  <td className="py-3 font-mono text-sm">${p.amount_usd}</td>
                  <td className="py-3 font-mono text-xs">{p.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </DashboardLayout>
  );
}
