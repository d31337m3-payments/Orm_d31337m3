import React, { useState } from "react";
import { Link } from "react-router-dom";
import Marquee from "react-fast-marquee";
import { motion, useScroll, useTransform } from "framer-motion";
import { Terminal, Shield, Database, Bell, Activity, Lock, Search, FileSignature, Gavel, Globe } from "lucide-react";
import FeatureDialog from "@/components/FeatureDialog";
import CanadaFlag from "@/components/CanadaFlag";

const BROKERS = ["SPOKEO","WHITEPAGES","ACXIOM","BEENVERIFIED","INTELIUS","MYLIFE","RADARIS","PEOPLEFINDER","TRUTHFINDER","INSTANTCHECKMATE","EQUIFAX","PEEKYOU","USSEARCH","FASTPEOPLESEARCH","GOOGLE","BING"];

const FEATURES = [
  {
    icon: Search, tag: "crawler",
    title: "Real Data Broker Crawling",
    short: "Real keyword scanning across 15+ broker sites, Google & Bing. Name, email, phone, address — we find it all.",
    body: "Our crawler probes Spokeo, BeenVerified, WhitePages, Intelius, MyLife, Radaris, Acxiom and 10+ others — plus live Google and Bing search results — every cycle. Every match is fingerprinted, classified by severity, and surfaced in your dashboard with a deep link to the offending page.",
    howItWorks: [
      "You add a name, email, phone, or address as a monitored keyword.",
      "Our crawler hits each broker + Google + Bing on schedule (Basic: weekly · Pro: daily · Enterprise: real-time).",
      "We classify findings by severity (Low → Critical) based on data type and broker reach.",
      "Anything new triggers an email alert in under 60 seconds.",
    ],
    stat: { label: "// brokers monitored", value: "15+" },
  },
  {
    icon: Activity, tag: "score",
    title: "Reputation Score 0-100",
    short: "Live score weighted by severity & broker reach. Watch your exposure shrink in real-time.",
    body: "Your Reputation Score is computed from every active finding, weighted by severity (Critical -15, High -10, Medium -5, Low -2) plus bonus credit for removals. Watch it climb from danger-zone red to safe-zone green as we clear each broker.",
    howItWorks: [
      "Score starts at 100 and is reduced for each active exposure.",
      "Removals earn back partial credit (+2 each, up to +15).",
      "Color-coded: Red (<40), Yellow (40-70), Green (70+).",
      "Updated on every scan cycle and removal confirmation.",
    ],
    stat: { label: "// avg score lift / 30 days", value: "+42" },
  },
  {
    icon: Bell, tag: "alerts",
    title: "Email Alerts in Real-Time",
    short: "The moment new data surfaces, you know. Configurable thresholds per keyword.",
    body: "Plain English alerts straight to your inbox the second something new is found. No spam, no marketing fluff — just a clean digest of what changed and what you can do about it.",
    howItWorks: [
      "Subscribe to a plan to enable email delivery via our private SMTP relay.",
      "Every successful scan with new findings triggers a digest email.",
      "Removal confirmations also land in your inbox.",
      "Configure thresholds (e.g., only High+ severity) per keyword in settings.",
    ],
    stat: { label: "// median alert latency", value: "<60s" },
  },
  {
    icon: Gavel, tag: "legal",
    title: "Legal Document Generation",
    short: "Auto-generate DMCA, Cease & Desist, CCPA and PIPEDA notices. E-signed. Ready to send.",
    body: "We generate jurisdiction-aware legal documents — DMCA takedown notices, cease & desist letters, CCPA / CPRA deletion requests, PIPEDA & Quebec Law 25 removal demands, and Right-to-be-Forgotten requests for Google & Bing — pre-filled with your data and ready to e-sign in one click.",
    howItWorks: [
      "Pick a finding from your dashboard.",
      "Choose the appropriate template (auto-filtered to your jurisdiction: 🇨🇦 🇺🇸 🇲🇽).",
      "Draw your e-signature once in the dashboard (ESIGN / UECA / LFFEA compliant).",
      "We affix your signature and dispatch to the broker. Track status until removed.",
    ],
    stat: { label: "// templates supported", value: "4 + counting" },
  },
  {
    icon: FileSignature, tag: "e-sign",
    title: "Built-in E-Signature",
    short: "Sign legal documents with a finger or mouse. Legally binding across North America.",
    body: "Draw your signature once. We securely attach it to every legal notice we send on your behalf — DMCA takedowns, removal requests, cease & desist. Binding under the U.S. ESIGN Act, Canada's PIPEDA + UECA, and Mexico's LFFEA.",
    howItWorks: [
      "Open the Documents → E-Signature tab in your dashboard.",
      "Type your full legal name and sign on the canvas.",
      "Your signature is stored encrypted, never reused without your action.",
      "Every signed document timestamps the IP, signer name, and applied jurisdiction.",
    ],
    stat: { label: "// legal frameworks", value: "ESIGN · UECA · LFFEA" },
  },
  {
    icon: Globe, tag: "search-engine",
    title: "Google & Bing De-indexing",
    short: "Right-to-be-Forgotten requests for the world's biggest search engines.",
    body: "Even if a data broker won't remove your info, we can get it de-indexed from Google and Bing — meaning searches for your name won't surface the page. We generate the legal de-indexing requests under Canadian PIPEDA and U.S. state privacy laws.",
    howItWorks: [
      "We scan Google & Bing search results for every monitored keyword.",
      "When a result surfaces personal data, we flag it as 'search-indexed'.",
      "Generate a Right-to-be-Forgotten request and we send it to the legal removals team.",
      "Track de-indexing status alongside broker removals.",
    ],
    stat: { label: "// search engines covered", value: "Google + Bing" },
  },
  {
    icon: Database, tag: "monitor",
    title: "Unlimited Keyword Monitoring",
    short: "Add names, aliases, emails, phone numbers. We watch them — forever.",
    body: "Add as many variations of your identity as you need: legal name, nicknames, maiden name, old emails, current and previous phone numbers, current and previous addresses. We track them all on one dashboard.",
    howItWorks: [
      "Basic: 5 keywords. Pro: 25. Enterprise: unlimited.",
      "Each keyword scanned on your plan's cadence.",
      "Click any keyword to scan it on-demand.",
      "Findings tagged back to the originating keyword for cleanup.",
    ],
    stat: { label: "// enterprise cap", value: "∞" },
  },
  {
    icon: Lock, tag: "payments",
    title: "Pay Your Way",
    short: "Interac e-Transfer, PayPal, or USDC on Base / Polygon / Ethereum. No card needed.",
    body: "Canadian-friendly Interac e-Transfer, global PayPal, or pseudonymous USDC stablecoin payments on Base, Polygon, or Ethereum. Crypto payments are auto-verified on-chain via direct RPC calls — no third-party processor.",
    howItWorks: [
      "Pick your plan in the Billing tab.",
      "Interac: send e-Transfer to payments@d31337m3.com with your account note.",
      "Crypto: send USDC to our wallet, paste the tx hash — we verify on-chain in real-time.",
      "PayPal: live checkout (when configured) for card-based payments.",
    ],
    stat: { label: "// payment methods", value: "3" },
  },
  {
    icon: Shield, tag: "tracker",
    title: "Removal Request Tracker",
    short: "One-click submission. We handle the broker correspondence and track every status.",
    body: "Every removal request you submit is logged, queued, and tracked from 'submitted' through 'pending' to 'removed'. We send the legal notices, follow up at the statutory intervals, and notify you when each one is closed.",
    howItWorks: [
      "Click 'Request Removal' on any finding.",
      "We auto-generate the appropriate legal notice based on the broker and your jurisdiction.",
      "Document is e-signed and dispatched to the broker's privacy office.",
      "Track status in real-time on your dashboard.",
    ],
    stat: { label: "// avg removal time", value: "7-21 days" },
  },
];

const Plan = ({ id, name, price, features, highlight }) => (
  <motion.div
    initial={{ opacity: 0, y: 30 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true, margin: "-50px" }}
    transition={{ duration: 0.5 }}
    whileHover={{ y: -4 }}
    data-testid={`plan-card-${id}`}
    className={`brutal-card p-8 ${highlight ? "border-[#FF3333]" : ""}`}
  >
    {highlight && <div className="overline text-[#FF3333] mb-3">// recommended</div>}
    <div className="font-display font-black text-3xl mb-1">{name}</div>
    <div className="font-mono text-zinc-500 mb-6">/* {id} */</div>
    <div className="font-display font-black text-5xl mb-1">${price}<span className="text-lg text-zinc-500">/mo</span></div>
    <ul className="mt-6 space-y-3 mb-8">
      {features.map(f => <li key={f} className="font-mono text-sm text-zinc-300 flex gap-2"><span className="text-[#FF3333]">›</span>{f}</li>)}
    </ul>
    <Link to="/register" data-testid={`select-plan-${id}`} className={`brutal-btn block text-center ${highlight ? "brutal-btn-primary" : ""}`}>Get Started</Link>
  </motion.div>
);

export default function Landing() {
  const [dialog, setDialog] = useState(null);
  const { scrollY } = useScroll();
  const heroY = useTransform(scrollY, [0, 500], [0, 150]);
  const heroOpacity = useTransform(scrollY, [0, 400], [1, 0.2]);

  return (
    <div className="min-h-screen bg-[#050505] text-white relative overflow-hidden">
      {/* Animated background grid */}
      <div className="fixed inset-0 pointer-events-none opacity-[0.04]" style={{
        backgroundImage: "linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)",
        backgroundSize: "60px 60px",
      }}/>
      {/* Scanline */}
      <motion.div
        animate={{ y: ["-10vh", "120vh"] }}
        transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
        className="fixed left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-[#FF3333]/30 to-transparent pointer-events-none z-0"
      />

      {/* Nav */}
      <nav className="glass-nav sticky top-0 z-50 px-8 py-4 flex items-center justify-between">
        <Link to="/" data-testid="logo-link" className="flex items-center gap-2">
          <Terminal className="text-[#FF3333]" size={20} />
          <span className="font-display font-black text-xl">d31337m3</span>
          <span className="ml-2 hidden sm:inline-flex items-center gap-1 font-mono text-[10px] tracking-widest text-zinc-500 border-l border-[#222] pl-3">
            <CanadaFlag size={10}/> MADE IN CANADA
          </span>
        </Link>
        <div className="flex items-center gap-6 font-mono text-sm">
          <a href="#features" className="text-zinc-400 hover:text-white">Features</a>
          <a href="#pricing" className="text-zinc-400 hover:text-white">Pricing</a>
          <Link to="/login" data-testid="nav-login" className="text-zinc-400 hover:text-white">Login</Link>
          <Link to="/register" data-testid="nav-register" className="brutal-btn brutal-btn-primary !py-2 !px-4 text-xs">Start</Link>
        </div>
      </nav>

      {/* Hero */}
      <motion.section style={{ y: heroY, opacity: heroOpacity }} className="hero-grain px-8 pt-24 pb-20 border-b border-[#222] relative">
        <div className="max-w-7xl mx-auto grid grid-cols-12 gap-6">
          <div className="col-span-12 md:col-span-8">
            <motion.div
              initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.5 }}
              className="overline text-[#FF3333] mb-6 flex items-center gap-3">
              <span>// online reputation management</span>
              <CanadaFlag size={10} />
              <span>built in canada</span>
            </motion.div>
            {["DELETE", "YOURSELF"].map((word, i) => (
              <motion.h1
                key={word}
                initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: i * 0.1 }}
                className="font-display font-black text-6xl md:text-8xl leading-[0.95] tracking-tighter uppercase"
              >{word}</motion.h1>
            ))}
            <motion.h1
              initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="font-display font-black text-6xl md:text-8xl leading-[0.95] tracking-tighter uppercase text-[#FF3333] mb-8"
            >FROM THE INTERNET.<span className="text-white blink">_</span></motion.h1>

            <motion.p
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4, duration: 0.6 }}
              className="font-mono text-lg text-zinc-400 max-w-2xl mb-10">
              We hunt down your data across 15+ data brokers, plus Google &amp; Bing, score your exposure, generate the legal paperwork, and submit the takedowns — all e-signed and tracked.<br/>
              <span className="text-white">No theatre. No fluff. Just clean.</span>
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }}
              className="flex flex-wrap gap-4">
              <Link to="/register" data-testid="hero-cta-primary" className="brutal-btn brutal-btn-primary">Start Free Trial →</Link>
              <a href="#features" data-testid="hero-cta-secondary" className="brutal-btn">View Capabilities</a>
            </motion.div>
          </div>

          {/* Live feed card */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.4, duration: 0.5 }}
            className="col-span-12 md:col-span-4 border border-[#222] p-6 bg-[#0a0a0a] font-mono text-xs relative">
            <div className="overline mb-3 flex items-center justify-between">
              <span>live.feed</span>
              <span className="flex items-center gap-1.5"><span className="w-2 h-2 bg-[#00FF41] rounded-full blink"/>LIVE</span>
            </div>
            {[
              ["spokeo.com", "1,284 records removed", "#00FF41"],
              ["whitepages.com", "892 records removed", "#00FF41"],
              ["beenverified.com", "743 records removed", "#00FF41"],
              ["google search", "146 urls de-indexed", "#00FF41"],
              ["bing search", "98 urls de-indexed", "#00FF41"],
              ["acxiom", "312 pending", "#FFD700"],
              ["intelius", "scan in progress", "#FF3333"],
            ].map(([name, status, color], i) => (
              <motion.div key={name}
                initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.6 + i * 0.08 }}
                className="text-zinc-400 mb-1">
                › <span style={{ color }}>{name}</span> · {status}{i === 6 && <span className="blink">_</span>}
              </motion.div>
            ))}
            <div className="mt-6 pt-4 border-t border-[#222]">
              <div className="overline mb-2">reputation_score</div>
              <motion.div
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.2 }}
                className="font-display font-black text-5xl text-[#00FF41]">87<span className="text-base text-zinc-500">/100</span></motion.div>
            </div>
          </motion.div>
        </div>
      </motion.section>

      {/* Marquee of brokers */}
      <section className="py-6 border-b border-[#222] bg-black">
        <div className="overline px-8 mb-3 flex items-center gap-3"><span>// targets neutralised</span></div>
        <Marquee speed={40} gradient={false} className="font-display font-black text-3xl text-zinc-700">
          {BROKERS.concat(BROKERS).map((b, i) => (
            <span key={i} className="px-8 hover:text-[#FF3333] transition-colors">{b} <span className="text-[#FF3333]">×</span></span>
          ))}
        </Marquee>
      </section>

      {/* Made-in-Canada strip */}
      <section className="border-b border-[#222] bg-gradient-to-r from-black via-[#180404] to-black py-8 px-8">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <CanadaFlag size={28} />
            <div>
              <div className="font-display font-black text-2xl tracking-tight">Made &amp; hosted in Canada. 🇨🇦</div>
              <div className="font-mono text-xs text-zinc-500 mt-1">Compliant with PIPEDA, Quebec Law 25, CCPA/CPRA, and LFPDPPP.</div>
            </div>
          </div>
          <div className="font-mono text-xs text-zinc-500 text-right">
            Coverage: <span className="text-white">🇨🇦 Canada · 🇺🇸 United States · 🇲🇽 México</span>
          </div>
        </div>
      </section>

      {/* Features grid (clickable) */}
      <section id="features" className="px-8 py-24 max-w-7xl mx-auto">
        <div className="overline text-[#FF3333] mb-4">// capabilities · click any card for details</div>
        <h2 className="font-display font-black text-5xl tracking-tighter mb-16 max-w-3xl">Every weapon you need to disappear, in one console.</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {FEATURES.map((f, i) => (
            <motion.button
              key={f.tag}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ duration: 0.4, delay: (i % 3) * 0.08 }}
              whileHover={{ y: -4, borderColor: "#fff" }}
              onClick={() => setDialog(f)}
              data-testid={`feature-card-${f.tag}`}
              className="brutal-card p-6 text-left cursor-pointer relative group"
            >
              <f.icon className="text-[#FF3333] mb-4" size={24} />
              <div className="font-display font-bold text-xl mb-2">{f.title}</div>
              <div className="font-mono text-sm text-zinc-400 leading-relaxed">{f.short}</div>
              <div className="absolute bottom-4 right-5 font-mono text-xs text-zinc-600 group-hover:text-[#FF3333] transition-colors">read →</div>
            </motion.button>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="px-8 py-24 border-t border-[#222] bg-black">
        <div className="max-w-7xl mx-auto">
          <div className="overline text-[#FF3333] mb-4">// pricing</div>
          <h2 className="font-display font-black text-5xl tracking-tighter mb-4">Pick your plan.</h2>
          <p className="font-mono text-zinc-500 mb-12">No contracts. Cancel any time. Pay in CAD, USD, or USDC.</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Plan id="basic" name="Basic" price={29} features={["5 keywords","Weekly scans","Email alerts","Reputation score"]} />
            <Plan id="pro" name="Pro" price={79} highlight features={["25 keywords","Daily scans","Email alerts","Removal requests","Legal documents (DMCA, C&D)","Priority queue"]} />
            <Plan id="enterprise" name="Enterprise" price={199} features={["Unlimited keywords","Real-time scans","Dedicated specialist","API access","White-glove removals","All legal templates"]} />
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[#222] px-8 py-12 bg-black">
        <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-8">
          <div>
            <div className="flex items-center gap-2 mb-3"><Terminal className="text-[#FF3333]" size={18}/><span className="font-display font-black">d31337m3</span></div>
            <div className="font-mono text-xs text-zinc-600">delete me, dot com.<br/>an uncompromising privacy weapon.</div>
          </div>
          <div className="font-mono text-xs text-zinc-500 space-y-1">
            <div className="overline mb-2 text-zinc-600">// jurisdictions</div>
            <div>🇨🇦 Canada — PIPEDA, Quebec Law 25</div>
            <div>🇺🇸 United States — CCPA, CPRA, DMCA</div>
            <div>🇲🇽 México — LFPDPPP</div>
          </div>
          <div className="font-mono text-xs text-zinc-500 md:text-right space-y-2">
            <div className="overline text-zinc-600 mb-2">// contact</div>
            <div>payments@d31337m3.com</div>
            <div>admin@d31337m3.com</div>
            <div className="flex items-center gap-2 md:justify-end mt-4 text-white">
              <CanadaFlag size={14}/> Made &amp; hosted in Canada · © 2026
            </div>
          </div>
        </div>
      </footer>

      {/* Feature Dialog */}
      <FeatureDialog open={!!dialog} onClose={() => setDialog(null)} feature={dialog} />
    </div>
  );
}
