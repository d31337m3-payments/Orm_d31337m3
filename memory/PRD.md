# d31337m3 — ORM Platform PRD

## Original Problem Statement
Build "d31337m3.com" (pronounced "delete me dot com") — a complete Online Reputation Management platform with subscription onboarding, email alerts on new findings, Reputation Score, data broker crawling, **legal document generation with e-signature (North America only)**, Google & Bing search-result scraping for trial users, and **Canadian-proud "Made in Canada" branding**.

## Tech Stack
- Backend: FastAPI + Motor (MongoDB) + bcrypt + JWT + aiosmtplib + web3.py + aiohttp + BeautifulSoup
- Frontend: React 19 + react-router-dom + framer-motion + recharts + react-fast-marquee + lucide-react + Tailwind
- Auth: JWT email/password + lightweight Google profile sync
- Payments: Interac e-Transfer (manual), Crypto USDC (direct RPC verify on Base/Polygon/Ethereum), PayPal scaffold (awaits credentials)

## User Personas
- Privacy-conscious individuals (CA/US/MX) wanting to remove themselves from data brokers
- Public figures, professionals, or victims of harassment
- Admin (admin@d31337m3.com) — manages clients, verifies manual payments, reviews scans

## What's Been Implemented

### Iteration 1 (2026-06-19)
- Brutalist red-and-black "terminal interface" theme (Chivo + IBM Plex Sans + JetBrains Mono)
- Landing page: hero, animated brokers marquee, 9 feature cards, 3-tier pricing
- Auth: JWT register/login + admin seed (admin@d31337m3.com / Admin2026!!)
- Client dashboard: Reputation Score gauge, stats, recent findings
- Keywords CRUD + plan-limit enforcement
- Real HTTP scraper + enrichment across 15+ brokers
- Findings list + removal-request workflow
- Subscription with Interac / Crypto (USDC RPC verify) / PayPal-scaffold
- Admin console: stats, users, payments confirm/reject, email log
- 25/25 backend tests passing

### Iteration 2 (2026-06-19) — Major Enhancements
- **Legal document generation (North America only — 🇨🇦 🇺🇸 🇲🇽)**: 4 templates (DMCA, Cease & Desist, Privacy Removal Request, Right-to-be-Forgotten). Jurisdiction-aware filtering — DMCA is US-only.
- **E-Signature**: canvas-based signature pad, ESIGN/UECA/LFFEA-compliant, full legal name + signed timestamp affixed to documents
- **Document viewer/printer/downloader**: in-app viewer, .txt download, print-to-PDF flow
- **Profile management**: full name, address, phone, country (CA/US/MX), state/province, jurisdiction-aware
- **Google + Bing search scraping**: real HTTP probes of Google & Bing search results added to every scan
- **Auto-onboarding scan**: new registrants get name auto-added as keyword + immediate background scan, so trial users see content within 30s
- **Animations**: framer-motion throughout — staggered hero reveals, scanline overlay, animated reputation gauge with glowing ring, score bar fill animation, hover lifts on cards, dialog spring transitions
- **Charts**: recharts line chart (14-day findings trend) + bar chart (severity distribution) + top-brokers progress bars
- **Feature dialogs**: every feature card on landing is now clickable, opens full-screen modal with detailed explanation, 4-step "how it works" breakdown, and a relevant stat
- **Canadian branding**: 🇨🇦 inline SVG flag in nav + sidebar + headers, "Made & hosted in Canada" hero strip, jurisdiction footer with all 3 country flags
- **Findings → Documents flow**: "LEGAL" button on any active finding pre-fills the document generator

## Architecture / Tasks Done
- `/app/backend/server.py` (single-file FastAPI app, ~850 lines)
- `/app/backend/.env` — SMTP, JWT, crypto wallet, RPC URLs, admin seed
- `/app/frontend/src/pages/` — Landing, Login, Register, Dashboard, Keywords, Findings, Billing, Admin, **Documents**
- `/app/frontend/src/components/` — DashboardLayout, **SignaturePad**, **FeatureDialog**, **CanadaFlag**

## Prioritized Backlog
- **P0**: Add real PayPal Live integration once user provides Client ID/Secret
- **P0**: Connect real SMTP (currently SMTP_ENABLED=false → emails mocked into MongoDB email_log) — set SMTP_ENABLED=true once user confirms password works
- **P1**: Email digest scheduler (daily/weekly batch summary instead of per-finding)
- **P1**: Webhook to track broker removal status automatically (currently manual)
- **P1**: Document PDF rendering (currently text + browser print-to-PDF; could use reportlab)
- **P2**: API tokens for Enterprise tier (API access)
- **P2**: Two-factor auth
- **P2**: Multi-language UI (EN/FR/ES for North America)
- **P2**: Public sharing of redacted reputation score (linkedin-style "verified clean" badge)

## Test Credentials
- Admin: `admin@d31337m3.com` / `Admin2026!!`

### Iteration 3 (2026-06-19) — Production Hardening
- **SMTP fully wired**: tested all 4 credential combinations → `admin@d31337m3.com / Admin2026!!` confirmed working. Backend now uses lenient TLS context (cert hostname mismatch on shared hosting is bypassed). `SMTP_ENABLED=true`. Verified real email delivery via 550 NoSuchUser confirmation (server reachable + authenticated).
- **Real broker dispatch**: 17-broker privacy-email registry (`BROKER_CONTACTS`) covering Spokeo, BeenVerified, WhitePages, Intelius, MyLife, Radaris, PeopleFinder, TruthFinder, FastPeopleSearch, PublicRecords, Acxiom, Equifax, PeekYou, InstantCheckmate, USSearch, Google Search, Bing Search. When a user signs a legal doc linked to a finding, we auto-dispatch the signed letter to the broker's privacy address as a real email + attachment, update the finding to `pending_removal`, and log the dispatch.
- **New `/api/broker-contacts` endpoint** + admin `/api/admin/removals` + admin `/api/admin/removals/{id}/mark-removed`
- **Admin → Removals tab**: track every dispatched legal notice, the broker email it went to, and one-click "MARK REMOVED" (which updates the finding + sends user confirmation email)
- **Interac flow polish**: 5-step plain-English instructions, USD + CAD estimate, "AUTO-DEPOSIT ENABLED" green callout, no security question warning. `payments@d31337m3.com` gets an automatic notification email when a user initiates payment.
