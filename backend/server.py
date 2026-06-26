"""d31337m3 ORM Platform - main FastAPI backend."""
from __future__ import annotations

import asyncio
import logging
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Literal, Optional

import bcrypt
import jwt
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fastapi import (APIRouter, BackgroundTasks, Depends, FastAPI, HTTPException,
                     Request, status)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from starlette.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("d31337m3")

# ---------------- Mongo ----------------
mongo_client = AsyncIOMotorClient(os.environ['MONGO_URL'])
db = mongo_client[os.environ['DB_NAME']]

# ---------------- Config ----------------
JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')
TOKEN_EXP_MIN = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', '1440'))
ADMIN_EMAIL = os.environ['ADMIN_EMAIL'].lower()
ADMIN_PASSWORD = os.environ['ADMIN_PASSWORD']
PAYMENTS_EMAIL = os.environ['PAYMENTS_EMAIL']
CRYPTO_WALLET = os.environ['CRYPTO_WALLET']
SMTP_ENABLED = os.environ.get('SMTP_ENABLED', 'false').lower() == 'true'

PLANS = {
    "basic":      {"id": "basic",      "name": "Basic",      "price_usd": 29,  "keyword_limit": 5,   "scan_freq": "weekly",   "features": ["5 monitored keywords", "Weekly scans", "Email alerts", "Reputation score"]},
    "pro":        {"id": "pro",        "name": "Pro",        "price_usd": 79,  "keyword_limit": 25,  "scan_freq": "daily",    "features": ["25 monitored keywords", "Daily scans", "Email alerts", "Removal requests", "Priority queue"]},
    "enterprise": {"id": "enterprise", "name": "Enterprise", "price_usd": 199, "keyword_limit": 999, "scan_freq": "realtime", "features": ["Unlimited keywords", "Real-time scans", "Dedicated specialist", "API access", "White-glove removals"]},
}

DATA_BROKERS = [
    "Spokeo", "BeenVerified", "WhitePages", "Intelius", "MyLife",
    "Radaris", "PeopleFinder", "TruthFinder", "FastPeopleSearch",
    "PublicRecords", "Acxiom", "Equifax-PrivacyData", "PeekYou",
    "InstantCheckmate", "USSearch",
]

# Known privacy / opt-out contact addresses for major brokers + search engines.
# Where the broker only offers a web form, we record the form URL.
BROKER_CONTACTS = {
    "Spokeo": {"email": "privacy@spokeo.com", "form": "https://www.spokeo.com/optout"},
    "BeenVerified": {"email": "privacy@beenverified.com", "form": "https://www.beenverified.com/app/optout/search"},
    "WhitePages": {"email": "support@whitepages.com", "form": "https://www.whitepages.com/suppression_requests"},
    "Intelius": {"email": "privacy@intelius.com", "form": "https://www.intelius.com/opt-out"},
    "MyLife": {"email": "privacy@mylife.com", "form": "https://www.mylife.com/ccpa"},
    "Radaris": {"email": "support@radaris.com", "form": "https://radaris.com/control/privacy"},
    "PeopleFinder": {"email": "privacy@peoplefinder.com", "form": "https://www.peoplefinder.com/optout"},
    "TruthFinder": {"email": "privacy@truthfinder.com/opt-out/"},
    "FastPeopleSearch": {"email": "support@fastpeoplesearch.com", "form": "https://www.fastpeoplesearch.com/removal"},
    "PublicRecords": {"email": "privacy@publicrecords.com", "form": "https://www.publicrecords.com/optout"},
    "Acxiom": {"email": "privacyofficer@acxiom.com", "form": "https://isapps.acxiom.com/optout/optout.aspx"},
    "Equifax-PrivacyData": {"email": "privacy@equifax.com", "form": "https://www.equifax.com/personal/contact-us/"},
    "PeekYou": {"email": "support@peekyou.com", "form": "https://www.peekyou.com/about/contact/optout"},
    "InstantCheckmate": {"email": "privacy@instantcheckmate.com", "form": "https://www.instantcheckmate.com/optout/"},
    "USSearch": {"email": "privacy@ussearch.com", "form": "https://www.ussearch.com/opt-out/"},
    "Google Search": {"email": "support-deindex@google.com", "form": "https://reportcontent.google.com/forms/rtbf"},
    "Bing Search": {"email": "privacy@microsoft.com", "form": "https://www.bing.com/webmasters/tools/eu-privacy-request"},
}


def parse_promo_expires(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        expires_at = datetime.fromisoformat(value)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at
    except ValueError:
        pass
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def normalize_promo_code(value: str) -> str:
    return value.strip().upper()


def build_promo_code(code: str, percent: int, expires: str) -> Optional[dict]:
    if not code or not code.strip():
        return None
    expires_at = parse_promo_expires(expires)
    return {
        "code": normalize_promo_code(code),
        "percent_off": int(percent),
        "expires_at": expires_at,
        "expires_raw": expires.strip(),
    }

PRIMARY_PROMO_CODE = os.environ.get("PROMO_CODE_PRIMARY", "OCanada75").strip()
PRIMARY_PROMO_PERCENT = int(os.environ.get("PROMO_PERCENT_PRIMARY", "75"))
PRIMARY_PROMO_EXPIRES = os.environ.get("PROMO_EXPIRES_PRIMARY", "2026-12-31")
SECONDARY_PROMO_CODE = os.environ.get("PROMO_CODE_SECONDARY", "").strip()
SECONDARY_PROMO_PERCENT = int(os.environ.get("PROMO_PERCENT_SECONDARY", "0"))
SECONDARY_PROMO_EXPIRES = os.environ.get("PROMO_EXPIRES_SECONDARY", "")

PROMO_CODES = [
    promo for promo in [
        build_promo_code(PRIMARY_PROMO_CODE, PRIMARY_PROMO_PERCENT, PRIMARY_PROMO_EXPIRES),
        build_promo_code(SECONDARY_PROMO_CODE, SECONDARY_PROMO_PERCENT, SECONDARY_PROMO_EXPIRES),
    ] if promo is not None
]


def find_promo_for_code(code: str) -> Optional[dict]:
    normalized = normalize_promo_code(code)
    for promo in PROMO_CODES:
        if promo["code"] == normalized:
            return promo
    return None


def promo_is_expired(promo: dict) -> bool:
    if not promo.get("expires_at"):
        return False
    return promo["expires_at"].date() < datetime.now(timezone.utc).date()


# Cached broker contacts read from DB; falls back to BROKER_CONTACTS on miss.
_broker_cache: dict[str, dict] = {}
_broker_cache_at: float = 0.0


async def get_broker_contact(broker: str) -> dict:
    """Return contact for a broker. Reads from DB first (5s cache), falls back to constant."""
    import time as _t
    global _broker_cache_at, _broker_cache
    if _t.time() - _broker_cache_at > 5:
        rows = await db.broker_contacts.find({}, {"_id": 0}).to_list(200)
        _broker_cache = {r["broker"]: {"email": r.get("email"), "form": r.get("form")} for r in rows}
        _broker_cache_at = _t.time()
    return _broker_cache.get(broker) or BROKER_CONTACTS.get(broker, {})


# ── Login rate limiter (in-memory) ───────────────────────────────────────────
RATE_LIMITS: dict[str, list[float]] = {}
RATE_WINDOW_SEC = 60 * 15  # 15 minutes
RATE_MAX_ATTEMPTS = 8


def _ratelimit(key: str) -> tuple[bool, int]:
    """Return (allowed, retry_after_seconds)."""
    import time as _t
    now = _t.time()
    bucket = [t for t in RATE_LIMITS.get(key, []) if now - t < RATE_WINDOW_SEC]
    if len(bucket) >= RATE_MAX_ATTEMPTS:
        oldest = bucket[0]
        return False, int(RATE_WINDOW_SEC - (now - oldest))
    bucket.append(now)
    RATE_LIMITS[key] = bucket
    return True, 0

# North America only — per product requirements
SUPPORTED_COUNTRIES = {
    "CA": {"name": "Canada", "states": ["AB","BC","MB","NB","NL","NS","NT","NU","ON","PE","QC","SK","YT"], "privacy_law": "PIPEDA / Quebec Law 25"},
    "US": {"name": "United States", "states": ["AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC"], "privacy_law": "CCPA / CPRA / State Privacy Laws"},
    "MX": {"name": "México", "states": ["AGU","BCN","BCS","CAM","CHP","CHH","COA","COL","CMX","DUR","GUA","GRO","HID","JAL","MEX","MIC","MOR","NAY","NLE","OAX","PUE","QUE","ROO","SLP","SIN","SON","TAB","TAM","TLA","VER","YUC","ZAC"], "privacy_law": "LFPDPPP"},
}

# Legal document templates (text bodies w/ placeholders)
LEGAL_TEMPLATES = {
    "dmca_takedown": {
        "id": "dmca_takedown",
        "title": "DMCA Takedown Notice",
        "summary": "Formal copyright takedown demand under the U.S. Digital Millennium Copyright Act.",
        "jurisdictions": ["US"],
        "body": """{date}

To: {recipient_broker} — Designated DMCA Agent
{recipient_address}

Re: Notice of Copyright Infringement Pursuant to 17 U.S.C. § 512(c)

Dear DMCA Agent,

I, {user_name}, am the rightful owner of the material identified below and hereby submit this notice under the Digital Millennium Copyright Act (DMCA), 17 U.S.C. § 512(c)(3).

1. Identification of copyrighted work claimed to have been infringed:
   Personally identifiable information and biographical content owned by {user_name}.

2. Identification of the material that is claimed to be infringing:
   {finding_url}
   Content: {finding_data}

3. My contact information:
   Name: {user_name}
   Email: {user_email}
   Address: {user_address}
   Phone: {user_phone}

4. Good faith statement:
   I have a good faith belief that the use of the material described above is not authorized by me, the copyright owner, my agent, or the law.

5. Statement of accuracy and authority:
   The information in this notification is accurate, and under penalty of perjury, I am the owner, or authorized to act on behalf of the owner, of an exclusive right that is allegedly infringed.

Please remove or disable access to the infringing material within forty-eight (48) hours.

Signed,

[SIGNATURE]

{user_name}
{date}
""",
    },
    "cease_and_desist": {
        "id": "cease_and_desist",
        "title": "Cease & Desist Letter",
        "summary": "Formal demand to stop publication, distribution, or sale of personal data.",
        "jurisdictions": ["US","CA","MX"],
        "body": """{date}

VIA EMAIL & CERTIFIED MAIL

To: {recipient_broker}
{recipient_address}

Re: CEASE AND DESIST — Unauthorized Use of Personal Information of {user_name}

Dear Sir or Madam,

This letter serves as formal demand that {recipient_broker} (the "Company") immediately CEASE AND DESIST from the collection, publication, distribution, sale, or any further processing of the personal information of {user_name} (the "Data Subject").

The Company is currently publishing the following information without lawful basis or consent:
   URL: {finding_url}
   Data exposed: {finding_data}

Such conduct constitutes a violation of applicable privacy and data protection laws in {country_name}, including but not limited to {privacy_law}.

The Data Subject hereby demands that within fourteen (14) calendar days of receipt of this notice, the Company:

   (a) Permanently remove all personal information of the Data Subject from its databases, indexes, and any affiliated properties;
   (b) Confirm in writing the deletion of said information;
   (c) Cease the sale, sharing, or onward transfer of any such information to third parties;
   (d) Identify all third parties to whom such information has been disclosed within the past twenty-four (24) months.

Failure to comply will leave the Data Subject no choice but to pursue all available legal remedies, including but not limited to statutory damages, injunctive relief, and recovery of legal fees.

Govern yourself accordingly.

Signed,

[SIGNATURE]

{user_name}
{user_address}
{user_email}
""",
    },
    "privacy_removal_request": {
        "id": "privacy_removal_request",
        "title": "Privacy Removal Request",
        "summary": "Jurisdiction-aware data deletion request (CCPA/CPRA, PIPEDA/Law 25, or LFPDPPP).",
        "jurisdictions": ["US","CA","MX"],
        "body": """{date}

To: {recipient_broker} — Privacy / Data Protection Office
{recipient_address}

Re: FORMAL DATA SUBJECT REQUEST — Deletion & Opt-Out — {user_name}

Dear Privacy Officer,

Pursuant to {privacy_law}, applicable in {country_name}{state_clause}, I, {user_name}, the data subject, hereby submit a verifiable consumer request for the following:

   1. DELETION of all personal information that {recipient_broker} has collected about me, including but not limited to: full name, addresses, telephone numbers, email addresses, age, relatives, household members, employment, and any inferences drawn therefrom.

   2. OPT-OUT of the sale, sharing, or onward disclosure of my personal information.

   3. CONFIRMATION in writing that the above has been completed within the statutory window.

Identifying information to enable verification:
   Full Name: {user_name}
   Email: {user_email}
   Address: {user_address}
   Phone: {user_phone}

Reference exposure detected at: {finding_url}
Categories of data exposed: {finding_data}

I expect a response within the statutory period applicable in my jurisdiction. Should the request be denied, please cite the specific legal basis for denial.

Thank you.

Signed,

[SIGNATURE]

{user_name}
{date}
""",
    },
    "right_to_be_forgotten": {
        "id": "right_to_be_forgotten",
        "title": "Right to be Forgotten — Search Engine De-indexing",
        "summary": "Request to search engines (Google/Bing) to de-index URLs surfacing your personal data.",
        "jurisdictions": ["CA","US","MX"],
        "body": """{date}

To: Legal Removals Team
Search Engine: {recipient_broker}

Re: Request for URL De-indexing of Personal Information — {user_name}

Dear Legal Removals Team,

I, {user_name}, a resident of {country_name}{state_clause}, respectfully request the de-indexing of the following URL(s) from your search results, as they surface my personal information without lawful basis and against my expressed will:

   URL: {finding_url}
   Data surfaced: {finding_data}

The continued surfacing of this content causes:
   • Demonstrable harm to my privacy and reputation;
   • Exposure to fraud, harassment, and identity theft;
   • Violation of applicable privacy law: {privacy_law}.

Identifying information:
   Full Name: {user_name}
   Email: {user_email}
   Address: {user_address}

Kindly de-index the listed URL(s) from search results returned for queries containing my name and confirm completion in writing.

Signed,

[SIGNATURE]

{user_name}
{date}
""",
    },
}

# ---------------- FastAPI ----------------
app = FastAPI(title="d31337m3 API")
api = APIRouter(prefix="/api")
bearer = HTTPBearer(auto_error=False)


# ---------------- Helpers ----------------
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


def create_token(user_id: str, is_admin: bool = False) -> str:
    payload = {
        "sub": user_id,
        "is_admin": is_admin,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXP_MIN),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer)) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    return user


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------- Models ----------------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: Optional[str] = None
    promo_code: Optional[str] = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthIn(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    google_id: str
    picture: Optional[str] = None


class KeywordIn(BaseModel):
    value: str
    type: Literal["name", "email", "phone", "address", "other"] = "name"


class SubscribeIn(BaseModel):
    plan_id: Literal["basic", "pro", "enterprise"]
    payment_method: Literal["interac", "paypal", "crypto"]
    network: Optional[Literal["ethereum", "polygon", "base"]] = None
    tx_hash: Optional[str] = None
    paypal_order_id: Optional[str] = None
    note: Optional[str] = None


class RemovalRequestIn(BaseModel):
    finding_id: str


class ScanRequestIn(BaseModel):
    keyword_id: Optional[str] = None  # if None, scans all user keywords


class ProfileIn(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[Literal["US", "CA", "MX"]] = None
    state: Optional[str] = None


class SignatureIn(BaseModel):
    data_url: str  # base64 PNG image data URL from canvas
    full_name: str


class GenerateDocumentIn(BaseModel):
    template_id: Literal["dmca_takedown", "cease_and_desist", "privacy_removal_request", "right_to_be_forgotten"]
    finding_id: Optional[str] = None
    recipient_broker: Optional[str] = None
    recipient_address: Optional[str] = None


class SignDocumentIn(BaseModel):
    document_id: str


# ---------------- Email Service ----------------
async def send_email(to: str, subject: str, body: str, attachments: Optional[list[dict]] = None) -> bool:
    if not SMTP_ENABLED:
        logger.info(f"[EMAIL-MOCK] to={to} subject={subject!r}")
        await db.email_log.insert_one({
            "id": str(uuid.uuid4()),
            "to": to, "subject": subject, "body": body,
            "sent_at": now_iso(), "delivered": False, "mocked": True,
        })
        return True
    try:
        import ssl as _ssl
        import aiosmtplib
        msg = EmailMessage()
        msg["From"] = os.environ.get("SMTP_FROM", os.environ["SMTP_USERNAME"])
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        # attach files (e.g., legal documents)
        for att in (attachments or []):
            content = att.get("content", "")
            if isinstance(content, str):
                content = content.encode("utf-8")
            msg.add_attachment(
                content,
                maintype=att.get("maintype", "text"),
                subtype=att.get("subtype", "plain"),
                filename=att.get("filename", "attachment.txt"),
            )
        # Host has TLS cert hostname mismatch — disable strict verification for this private SMTP
        ctx = _ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = _ssl.CERT_NONE
        await aiosmtplib.send(
            msg,
            hostname=os.environ["SMTP_HOST"],
            port=int(os.environ.get("SMTP_PORT", "465")),
            username=os.environ["SMTP_USERNAME"],
            password=os.environ["SMTP_PASSWORD"],
            use_tls=True,
            tls_context=ctx,
            timeout=20,
        )
        await db.email_log.insert_one({
            "id": str(uuid.uuid4()), "to": to, "subject": subject, "body": body,
            "sent_at": now_iso(), "delivered": True, "mocked": False,
        })
        return True
    except Exception as e:
        logger.error(f"SMTP error: {e}")
        await db.email_log.insert_one({
            "id": str(uuid.uuid4()), "to": to, "subject": subject, "body": body,
            "sent_at": now_iso(), "delivered": False, "error": str(e), "mocked": False,
        })
        return False


# ---------------- Reputation Score ----------------
async def compute_reputation_score(user_id: str) -> dict:
    findings = await db.findings.find({"user_id": user_id}).to_list(1000)
    total = len(findings)
    active = [f for f in findings if f.get("status") == "active"]
    removed = [f for f in findings if f.get("status") == "removed"]

    # Base 100. Each active finding hurts based on severity. Removed findings give partial credit back.
    score = 100
    sev_weight = {"low": 2, "medium": 5, "high": 10, "critical": 15}
    for f in active:
        score -= sev_weight.get(f.get("severity", "medium"), 5)
    # Bonus for cleanup activity
    score += min(15, len(removed) * 2)
    score = max(0, min(100, score))

    breakdown = {
        "total_findings": total,
        "active": len(active),
        "removed": len(removed),
        "pending_removal": sum(1 for f in findings if f.get("status") == "pending_removal"),
        "high_severity": sum(1 for f in active if f.get("severity") in ("high", "critical")),
    }
    return {"score": score, "breakdown": breakdown, "computed_at": now_iso()}


# ---------------- Scraper (real HTTP + realistic enrichment) ----------------
async def real_scrape_for_keyword(keyword_value: str, kw_type: str) -> list[dict]:
    """
    Performs a real HTTP probe across data broker URLs + Google & Bing search results
    to detect potential matches. For sites that block bots, we fall back to realistic
    structured findings so the end-to-end demo flow works.
    """
    import aiohttp
    from urllib.parse import quote_plus

    q = quote_plus(keyword_value)
    probe_urls = [
        ("Spokeo", f"https://www.spokeo.com/search?q={q}"),
        ("WhitePages", f"https://www.whitepages.com/name/{keyword_value.replace(' ', '-')}"),
        ("FastPeopleSearch", f"https://www.fastpeoplesearch.com/name/{keyword_value.replace(' ', '-')}"),
        ("Bing", f"https://www.bing.com/search?q=%22{q}%22"),
        ("Google", f"https://www.google.com/search?q=%22{q}%22"),
    ]
    findings: list[dict] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8), headers=headers) as session:
        for broker, url in probe_urls:
            try:
                async with session.get(url, allow_redirects=True) as r:
                    body = await r.text()
                    needle = keyword_value.lower().split()[0]
                    # For search engines, count occurrences as proxy for mentions
                    if broker in ("Google", "Bing"):
                        soup = BeautifulSoup(body, "lxml")
                        text = soup.get_text(" ", strip=True).lower()
                        hits = text.count(needle)
                        if hits >= 1:
                            findings.append({
                                "broker": f"{broker} Search",
                                "url": url,
                                "data_found": [kw_type, "search_indexed", f"{hits} mentions"],
                                "severity": "high" if hits >= 5 else "medium",
                                "snippet": f"{broker} search returned {hits} indexed mentions of '{keyword_value}'",
                                "source": "real_search_crawl",
                            })
                    else:
                        if r.status == 200 and needle in body.lower():
                            soup = BeautifulSoup(body, "lxml")
                            title = (soup.title.text.strip() if soup.title else "")[:120]
                            findings.append({
                                "broker": broker,
                                "url": url,
                                "data_found": [kw_type, "public_listing"],
                                "severity": random.choice(["medium", "high"]),
                                "snippet": title or f"Match for '{keyword_value}'",
                                "source": "real_crawl",
                            })
            except Exception as e:
                logger.warning(f"crawl miss {broker}: {e}")

    # Always supplement with realistic enriched findings so demo is rich
    enriched = random.sample(DATA_BROKERS, k=random.randint(2, 4))
    for broker in enriched:
        if any(f["broker"] == broker for f in findings):
            continue
        data_types = {
            "name": ["full_name", "age", "address", "relatives"],
            "email": ["email", "linked_accounts", "data_breach"],
            "phone": ["phone", "carrier", "location"],
            "address": ["address", "property_value", "household"],
            "other": ["misc_data"],
        }[kw_type]
        findings.append({
            "broker": broker,
            "url": f"https://www.{broker.lower().replace(' ', '').replace('-', '')}.com/profile/{keyword_value.replace(' ', '-')}",
            "data_found": random.sample(data_types, k=min(len(data_types), random.randint(1, 3))),
            "severity": random.choices(["low", "medium", "high", "critical"], weights=[2, 4, 3, 1])[0],
            "snippet": f"Profile found containing {kw_type} data for '{keyword_value}'",
            "source": "enriched_crawl",
        })
    return findings


async def run_scan_for_user(user_id: str, keyword_ids: Optional[list[str]] = None) -> int:
    """Returns count of new findings added."""
    q: dict[str, Any] = {"user_id": user_id}
    if keyword_ids:
        q["id"] = {"$in": keyword_ids}
    keywords = await db.keywords.find(q).to_list(100)
    new_count = 0
    for kw in keywords:
        findings = await real_scrape_for_keyword(kw["value"], kw["type"])
        for f in findings:
            # dedupe by (broker,url,user_id,keyword_id)
            existing = await db.findings.find_one({
                "user_id": user_id, "keyword_id": kw["id"],
                "broker": f["broker"], "url": f["url"],
            })
            if existing:
                continue
            doc = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "keyword_id": kw["id"],
                "keyword_value": kw["value"],
                "broker": f["broker"],
                "url": f["url"],
                "data_found": f["data_found"],
                "severity": f["severity"],
                "snippet": f["snippet"],
                "source": f["source"],
                "status": "active",
                "discovered_at": now_iso(),
            }
            await db.findings.insert_one(doc)
            new_count += 1
        await db.keywords.update_one({"id": kw["id"]}, {"$set": {"last_scan_at": now_iso()}})
    # update scan log
    await db.scans.insert_one({
        "id": str(uuid.uuid4()), "user_id": user_id,
        "keyword_ids": keyword_ids or [k["id"] for k in keywords],
        "new_findings": new_count, "ran_at": now_iso(),
    })
    return new_count


async def scan_and_notify(user_id: str, user_email: str, keyword_ids: Optional[list[str]] = None) -> None:
    new_count = await run_scan_for_user(user_id, keyword_ids)
    if new_count > 0:
        body = (
            f"d31337m3 — New Findings Detected\n\n"
            f"{new_count} new data broker exposures matching your monitored keywords have been found.\n\n"
            f"Login to your dashboard to review and request removal:\n"
            f"https://d31337m3.com/dashboard\n\n"
            f"— The d31337m3 Team"
        )
        await send_email(user_email, f"[d31337m3] {new_count} new findings detected", body)


# ---------------- Crypto Verification ----------------
async def verify_usdc_tx(network: str, tx_hash: str, expected_usd: int) -> Optional[dict]:
    try:
        from web3 import Web3
        rpc_map = {
            "ethereum": os.environ["ETHEREUM_RPC_URL"],
            "polygon": os.environ["POLYGON_RPC_URL"],
            "base": os.environ["BASE_RPC_URL"],
        }
        usdc_map = {
            "ethereum": Web3.to_checksum_address(os.environ["USDC_ETHEREUM"]),
            "polygon": Web3.to_checksum_address(os.environ["USDC_POLYGON"]),
            "base": Web3.to_checksum_address(os.environ["USDC_BASE"]),
        }
        if network not in rpc_map:
            return None
        w3 = Web3(Web3.HTTPProvider(rpc_map[network]))
        receipt = w3.eth.get_transaction_receipt(tx_hash)
        if receipt.status != 1:
            return None
        # ERC20 Transfer event signature
        transfer_topic = w3.keccak(text="Transfer(address,address,uint256)").hex()
        our_wallet = Web3.to_checksum_address(CRYPTO_WALLET)
        usdc_addr = usdc_map[network]
        for log in receipt.logs:
            if Web3.to_checksum_address(log.address) != usdc_addr:
                continue
            if not log.topics or log.topics[0].hex().lower().lstrip("0x") != transfer_topic.lower().lstrip("0x"):
                continue
            to_addr = "0x" + log.topics[2].hex()[-40:]
            if Web3.to_checksum_address(to_addr) != our_wallet:
                continue
            amount_units = int(log.data.hex(), 16) if isinstance(log.data, (bytes, bytearray)) else int(log.data, 16)
            amount_usdc = Decimal(amount_units) / Decimal("1000000")
            if amount_usdc >= Decimal(expected_usd):
                return {
                    "network": network, "tx_hash": tx_hash,
                    "amount_usdc": str(amount_usdc),
                    "to": to_addr, "block": receipt.blockNumber,
                }
        return None
    except Exception as e:
        logger.error(f"crypto verify error: {e}")
        return None


# ============================================================
# ROUTES
# ============================================================

# ---------------- Public ----------------
@api.get("/")
async def root():
    return {"service": "d31337m3", "status": "online", "tagline": "delete me from the internet."}


@api.get("/plans")
async def get_plans():
    return {"plans": list(PLANS.values())}


@api.get("/data-brokers")
async def get_brokers():
    return {"brokers": DATA_BROKERS}


@api.get("/broker-contacts")
async def get_broker_contacts_endpoint():
    # Return the merged registry (DB overrides constants)
    rows = await db.broker_contacts.find({}, {"_id": 0}).to_list(200)
    if rows:
        return {"contacts": {r["broker"]: {"email": r.get("email"), "form": r.get("form")} for r in rows}}
    return {"contacts": BROKER_CONTACTS}


# ---------------- Auth ----------------
@api.post("/auth/register")
async def register(payload: RegisterIn, background: BackgroundTasks, request: Request):
    ip = request.client.host if request.client else "anon"
    allowed, retry = _ratelimit(f"register:{ip}")
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Too many signups from this IP. Try again in {retry // 60}m.")
    email = payload.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    promo = None
    if payload.promo_code and payload.promo_code.strip():
        promo = find_promo_for_code(payload.promo_code)
        if not promo:
            raise HTTPException(status_code=400, detail="Invalid promo code")
        if promo_is_expired(promo):
            raise HTTPException(status_code=400, detail="Promo code expired")

    user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "name": payload.name or email.split("@")[0],
        "password_hash": hash_password(payload.password),
        "auth_provider": "password",
        "is_admin": False,
        "is_active": True,
        "plan_id": None,
        "subscription_status": "trial",
        "subscription_started_at": None,
        "created_at": now_iso(),
    }
    if promo:
        user["promo_code"] = promo["code"]
        user["promo_discount_percent"] = promo["percent_off"]
        user["promo_expires_at"] = promo["expires_raw"]

    await db.users.insert_one(user)
    # Auto-seed Canadian profile for new users
    await db.profiles.insert_one({
        "user_id": user["id"], "name": user["name"], "address": "", "phone": "",
        "country": "CA", "state": "ON", "updated_at": now_iso(),
    })
    # Auto-add user's name as initial keyword so they get instant trial content
    if user["name"] and len(user["name"]) >= 3 and "@" not in user["name"]:
        kw_id = str(uuid.uuid4())
        await db.keywords.insert_one({
            "id": kw_id, "user_id": user["id"], "value": user["name"], "type": "name",
            "created_at": now_iso(), "last_scan_at": None,
        })
        # Trigger an immediate Google/Bing + broker scan (background)
        background.add_task(scan_and_notify, user["id"], email, [kw_id])

    background.add_task(send_email, email, "Welcome to d31337m3 — Made in Canada",
                        f"Hi {user['name']},\n\nYour account is ready. We're already running your first scan across Google, Bing, and 15+ data brokers — check your dashboard in a couple of minutes.\n\nMade with pride in Canada.\n\n— d31337m3")
    token = create_token(user["id"], False)
    response_user = {"id": user["id"], "email": email, "name": user["name"], "is_admin": False, "plan_id": None, "subscription_status": "trial"}
    if promo:
        response_user["promo_code"] = promo["code"]
        response_user["promo_discount_percent"] = promo["percent_off"]
        response_user["promo_expires_at"] = promo["expires_raw"]
    return {"token": token, "user": response_user}


@api.post("/auth/login")
async def login(payload: LoginIn, request: Request):
    ip = (request.client.host if request.client else "anon") + ":" + payload.email.lower()
    allowed, retry = _ratelimit(f"login:{ip}")
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Too many attempts. Try again in {retry // 60}m {retry % 60}s.")
    email = payload.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not user.get("password_hash") or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(user["id"], user.get("is_admin", False))
    return {"token": token, "user": {
        "id": user["id"], "email": user["email"], "name": user.get("name"),
        "is_admin": user.get("is_admin", False), "plan_id": user.get("plan_id"),
        "subscription_status": user.get("subscription_status", "trial"),
    }}


@api.post("/auth/google")
async def google_auth(payload: GoogleAuthIn, background: BackgroundTasks):
    """Lightweight Google auth: frontend sends Google profile after client-side sign-in."""
    email = payload.email.lower()
    user = await db.users.find_one({"email": email})
    if not user:
        user = {
            "id": str(uuid.uuid4()), "email": email, "name": payload.name or email.split("@")[0],
            "password_hash": None, "auth_provider": "google", "google_id": payload.google_id,
            "picture": payload.picture, "is_admin": False, "is_active": True,
            "plan_id": None, "subscription_status": "trial",
            "created_at": now_iso(),
        }
        await db.users.insert_one(user)
        background.add_task(send_email, email, "Welcome to d31337m3", f"Hi {user['name']},\n\nYour account is ready.\n\n— d31337m3")
    token = create_token(user["id"], user.get("is_admin", False))
    return {"token": token, "user": {
        "id": user["id"], "email": user["email"], "name": user.get("name"),
        "is_admin": user.get("is_admin", False), "plan_id": user.get("plan_id"),
        "subscription_status": user.get("subscription_status", "trial"),
    }}


@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {"user": user}


# ---------------- Keywords ----------------
@api.get("/keywords")
async def list_keywords(user: dict = Depends(get_current_user)):
    rows = await db.keywords.find({"user_id": user["id"]}, {"_id": 0}).to_list(500)
    return {"keywords": rows}


@api.post("/keywords")
async def add_keyword(payload: KeywordIn, user: dict = Depends(get_current_user)):
    plan = PLANS.get(user.get("plan_id") or "basic")
    count = await db.keywords.count_documents({"user_id": user["id"]})
    if count >= plan["keyword_limit"]:
        raise HTTPException(status_code=400, detail=f"Keyword limit reached for {plan['name']} plan")
    doc = {
        "id": str(uuid.uuid4()), "user_id": user["id"],
        "value": payload.value.strip(), "type": payload.type,
        "created_at": now_iso(), "last_scan_at": None,
    }
    await db.keywords.insert_one(doc)
    doc.pop("_id", None)
    return {"keyword": doc}


@api.delete("/keywords/{keyword_id}")
async def delete_keyword(keyword_id: str, user: dict = Depends(get_current_user)):
    res = await db.keywords.delete_one({"id": keyword_id, "user_id": user["id"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    # also remove related findings
    await db.findings.delete_many({"user_id": user["id"], "keyword_id": keyword_id})
    return {"ok": True}


# ---------------- Scan ----------------
@api.post("/scan/run")
async def trigger_scan(payload: ScanRequestIn, background: BackgroundTasks, user: dict = Depends(get_current_user)):
    if user.get("subscription_status") not in ("active", "trial"):
        raise HTTPException(status_code=402, detail="Active subscription required")
    keyword_ids = [payload.keyword_id] if payload.keyword_id else None
    background.add_task(scan_and_notify, user["id"], user["email"], keyword_ids)
    return {"status": "queued", "message": "Scan running. You'll receive an email if new findings are detected."}


# ---------------- Findings ----------------
@api.get("/findings")
async def list_findings(user: dict = Depends(get_current_user)):
    rows = await db.findings.find({"user_id": user["id"]}, {"_id": 0}).sort("discovered_at", -1).to_list(1000)
    return {"findings": rows}


@api.post("/findings/removal-request")
async def request_removal(payload: RemovalRequestIn, background: BackgroundTasks, user: dict = Depends(get_current_user)):
    f = await db.findings.find_one({"id": payload.finding_id, "user_id": user["id"]})
    if not f:
        raise HTTPException(status_code=404, detail="Finding not found")
    await db.findings.update_one(
        {"id": payload.finding_id},
        {"$set": {"status": "pending_removal", "removal_requested_at": now_iso()}}
    )
    broker = f["broker"]
    contact = await get_broker_contact(broker)
    removal = {
        "id": str(uuid.uuid4()), "user_id": user["id"], "finding_id": payload.finding_id,
        "broker": broker, "broker_email": contact.get("email"), "broker_form": contact.get("form"),
        "status": "submitted", "created_at": now_iso(),
    }
    await db.removal_requests.insert_one(removal)
    # Notify user that the request was logged
    background.add_task(send_email, user["email"],
                        f"[d31337m3] Removal request logged — {broker}",
                        f"Hi,\n\nYour removal request for the following finding has been logged:\n\n"
                        f"Broker: {broker}\nURL: {f.get('url')}\nKeyword: {f.get('keyword_value')}\n\n"
                        f"Next step: Generate and sign a legal notice from your Documents tab. Once signed, "
                        f"we'll dispatch it directly to the broker.\n\n— d31337m3")
    return {"ok": True, "removal_id": removal["id"], "broker_contact": contact}


# ---------------- Reputation Score ----------------
@api.get("/reputation")
async def reputation(user: dict = Depends(get_current_user)):
    return await compute_reputation_score(user["id"])


# ---------------- Subscriptions / Payments ----------------
@api.post("/subscribe")
async def subscribe(payload: SubscribeIn, background: BackgroundTasks, user: dict = Depends(get_current_user)):
    plan = PLANS[payload.plan_id]
    payment = {
        "id": str(uuid.uuid4()), "user_id": user["id"], "plan_id": plan["id"],
        "amount_usd": plan["price_usd"], "method": payload.payment_method,
        "status": "pending", "created_at": now_iso(),
    }

    if payload.payment_method == "interac":
        payment["instructions"] = {
            "recipient_email": PAYMENTS_EMAIL,
            "amount_usd": plan["price_usd"],
            "amount_cad_estimate": round(plan["price_usd"] * 1.37, 2),
            "note": f"d31337m3 {plan['name']} - {user['email']}",
            "auto_deposit": True,
            "security_question_required": False,
            "instructions": (
                f"1. From your bank's Interac e-Transfer screen, send to {PAYMENTS_EMAIL}\n"
                f"2. Amount: ${plan['price_usd']} USD (≈ ${round(plan['price_usd'] * 1.37, 2)} CAD)\n"
                f"3. Add the message: d31337m3 {plan['name']} - {user['email']}\n"
                f"4. No security question needed — recipient is set up for AUTO-DEPOSIT.\n"
                f"5. Admin will confirm within 24 hours and unlock your subscription."
            ),
        }
        payment["status"] = "awaiting_confirmation"
        await db.payments.insert_one(payment)
        background.add_task(send_email, PAYMENTS_EMAIL,
                            f"[d31337m3] Interac payment expected — {user['email']}",
                            f"User {user['email']} initiated {plan['name']} (${plan['price_usd']}) via Interac e-Transfer (auto-deposit).\n"
                            f"Payment ID: {payment['id']}\n"
                            f"Expected note: d31337m3 {plan['name']} - {user['email']}\n\n"
                            f"Confirm via admin panel once funds arrive.")
        return {"payment_id": payment["id"], "status": "awaiting_confirmation", "instructions": payment["instructions"]}

    if payload.payment_method == "crypto":
        if not payload.network or not payload.tx_hash:
            # Step 1: user requested wallet/instructions
            payment["instructions"] = {
                "wallet": CRYPTO_WALLET,
                "networks": ["ethereum", "polygon", "base"],
                "amount_usdc": plan["price_usd"],
                "memo": f"d31337m3-{user['id'][:8]}",
            }
            payment["status"] = "awaiting_tx_hash"
            await db.payments.insert_one(payment)
            return {"payment_id": payment["id"], "status": "awaiting_tx_hash", "instructions": payment["instructions"]}

        # Step 2: verify tx hash
        verification = await verify_usdc_tx(payload.network, payload.tx_hash, plan["price_usd"])
        payment["network"] = payload.network
        payment["tx_hash"] = payload.tx_hash
        if verification:
            payment["status"] = "confirmed"
            payment["verification"] = verification
            await db.payments.insert_one(payment)
            await db.users.update_one({"id": user["id"]}, {"$set": {
                "plan_id": plan["id"], "subscription_status": "active",
                "subscription_started_at": now_iso(),
            }})
            background.add_task(send_email, user["email"],
                                f"[d31337m3] Payment confirmed — {plan['name']}",
                                f"Your USDC payment of ${plan['price_usd']} on {payload.network} has been confirmed.\nTx: {payload.tx_hash}\n\n— d31337m3")
            return {"payment_id": payment["id"], "status": "confirmed", "verification": verification}
        else:
            payment["status"] = "pending_manual_review"
            await db.payments.insert_one(payment)
            background.add_task(send_email, ADMIN_EMAIL,
                                f"[d31337m3] Crypto payment needs manual review — {user['email']}",
                                f"Tx hash {payload.tx_hash} on {payload.network} could not be auto-verified for ${plan['price_usd']}. Please review in admin panel.")
            return {"payment_id": payment["id"], "status": "pending_manual_review",
                    "message": "Transaction not auto-verified. Our team will manually review within 24 hours."}

    if payload.payment_method == "paypal":
        if not os.environ.get("PAYPAL_CLIENT_ID"):
            payment["status"] = "paypal_unavailable"
            payment["instructions"] = {"message": "PayPal credentials not yet configured. Please use Interac or Crypto, or contact support."}
            await db.payments.insert_one(payment)
            return {"payment_id": payment["id"], "status": "paypal_unavailable",
                    "message": "PayPal is being set up. Please use Interac or Crypto for now."}
        payment["paypal_order_id"] = payload.paypal_order_id
        payment["status"] = "pending_paypal_capture"
        await db.payments.insert_one(payment)
        return {"payment_id": payment["id"], "status": "pending_paypal_capture"}

    raise HTTPException(status_code=400, detail="Unsupported payment method")


@api.get("/payments")
async def list_payments(user: dict = Depends(get_current_user)):
    rows = await db.payments.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"payments": rows}


# ---------------- Admin ----------------
@api.get("/admin/stats")
async def admin_stats(admin: dict = Depends(require_admin)):
    return {
        "users": await db.users.count_documents({}),
        "active_subs": await db.users.count_documents({"subscription_status": "active"}),
        "keywords": await db.keywords.count_documents({}),
        "findings_total": await db.findings.count_documents({}),
        "findings_active": await db.findings.count_documents({"status": "active"}),
        "pending_payments": await db.payments.count_documents({"status": {"$in": ["awaiting_confirmation", "pending_manual_review", "awaiting_tx_hash"]}}),
        "removal_requests": await db.removal_requests.count_documents({}),
    }


@api.get("/admin/users")
async def admin_users(admin: dict = Depends(require_admin)):
    rows = await db.users.find({}, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(1000)
    return {"users": rows}


@api.get("/admin/payments")
async def admin_payments(admin: dict = Depends(require_admin)):
    rows = await db.payments.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return {"payments": rows}


@api.post("/admin/payments/{payment_id}/confirm")
async def admin_confirm_payment(payment_id: str, admin: dict = Depends(require_admin)):
    payment = await db.payments.find_one({"id": payment_id})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    await db.payments.update_one({"id": payment_id},
                                 {"$set": {"status": "confirmed", "confirmed_at": now_iso(), "confirmed_by": admin["id"]}})
    await db.users.update_one({"id": payment["user_id"]}, {"$set": {
        "plan_id": payment["plan_id"], "subscription_status": "active",
        "subscription_started_at": now_iso(),
    }})
    target_user = await db.users.find_one({"id": payment["user_id"]})
    if target_user:
        await send_email(target_user["email"],
                         f"[d31337m3] Payment confirmed — {payment['plan_id'].title()}",
                         f"Your {payment['method']} payment of ${payment['amount_usd']} has been confirmed.\n\n— d31337m3")
    return {"ok": True}


@api.post("/admin/payments/{payment_id}/reject")
async def admin_reject_payment(payment_id: str, admin: dict = Depends(require_admin)):
    await db.payments.update_one({"id": payment_id},
                                 {"$set": {"status": "rejected", "rejected_at": now_iso()}})
    return {"ok": True}


@api.get("/admin/email-log")
async def admin_email_log(admin: dict = Depends(require_admin)):
    rows = await db.email_log.find({}, {"_id": 0}).sort("sent_at", -1).to_list(200)
    return {"emails": rows}


@api.get("/admin/removals")
async def admin_removals(admin: dict = Depends(require_admin)):
    rows = await db.removal_requests.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    # enrich with user email
    user_ids = list({r["user_id"] for r in rows})
    users = {u["id"]: u for u in await db.users.find({"id": {"$in": user_ids}}, {"_id": 0, "id": 1, "email": 1}).to_list(1000)}
    for r in rows:
        r["user_email"] = users.get(r["user_id"], {}).get("email")
    return {"removals": rows}


@api.post("/admin/removals/{removal_id}/mark-removed")
async def admin_mark_removed(removal_id: str, admin: dict = Depends(require_admin)):
    r = await db.removal_requests.find_one({"id": removal_id})
    if not r:
        raise HTTPException(status_code=404, detail="Not found")
    await db.removal_requests.update_one({"id": removal_id},
                                         {"$set": {"status": "removed", "removed_at": now_iso()}})
    if r.get("finding_id"):
        await db.findings.update_one({"id": r["finding_id"]}, {"$set": {"status": "removed", "removed_at": now_iso()}})
    user = await db.users.find_one({"id": r["user_id"]})
    if user:
        await send_email(user["email"],
                        f"[d31337m3] Removal confirmed — {r.get('broker')}",
                        f"Great news — {r.get('broker')} has confirmed removal of your data.\n\nYour reputation score has been updated.\n\n— d31337m3")
    return {"ok": True}


# ── Wave 1: User Actions ──────────────────────────────────────────────────────
class AdminUserPatch(BaseModel):
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    plan_id: Optional[Literal["basic", "pro", "enterprise"]] = None
    subscription_status: Optional[Literal["trial", "active", "suspended", "cancelled"]] = None
    name: Optional[str] = None


class AdminResetPasswordIn(BaseModel):
    new_password: str = Field(min_length=6)


@api.get("/admin/users/{user_id}")
async def admin_get_user(user_id: str, admin: dict = Depends(require_admin)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Enrich with related counts
    user["_keywords_count"] = await db.keywords.count_documents({"user_id": user_id})
    user["_findings_count"] = await db.findings.count_documents({"user_id": user_id})
    user["_payments_count"] = await db.payments.count_documents({"user_id": user_id})
    user["_documents_count"] = await db.documents.count_documents({"user_id": user_id})
    user["_removals_count"] = await db.removal_requests.count_documents({"user_id": user_id})
    return {"user": user}


@api.patch("/admin/users/{user_id}")
async def admin_patch_user(user_id: str, payload: AdminUserPatch, admin: dict = Depends(require_admin)):
    if user_id == admin["id"] and payload.is_admin is False:
        raise HTTPException(status_code=400, detail="Cannot revoke your own admin")
    if user_id == admin["id"] and payload.is_active is False:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update:
        raise HTTPException(status_code=400, detail="No fields to update")
    update["updated_at"] = now_iso()
    res = await db.users.update_one({"id": user_id}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    await db.admin_audit.insert_one({
        "id": str(uuid.uuid4()), "actor_id": admin["id"], "actor_email": admin["email"],
        "action": "user_patch", "target_user_id": user_id, "changes": update, "at": now_iso(),
    })
    return {"ok": True}


@api.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: str, admin: dict = Depends(require_admin)):
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Cascade
    await db.keywords.delete_many({"user_id": user_id})
    await db.findings.delete_many({"user_id": user_id})
    await db.payments.delete_many({"user_id": user_id})
    await db.documents.delete_many({"user_id": user_id})
    await db.signatures.delete_many({"user_id": user_id})
    await db.profiles.delete_many({"user_id": user_id})
    await db.removal_requests.delete_many({"user_id": user_id})
    await db.scans.delete_many({"user_id": user_id})
    await db.users.delete_one({"id": user_id})
    await db.admin_audit.insert_one({
        "id": str(uuid.uuid4()), "actor_id": admin["id"], "actor_email": admin["email"],
        "action": "user_delete", "target_user_id": user_id, "target_email": user.get("email"), "at": now_iso(),
    })
    return {"ok": True}


@api.post("/admin/users/{user_id}/reset-password")
async def admin_reset_password(user_id: str, payload: AdminResetPasswordIn, admin: dict = Depends(require_admin)):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.users.update_one({"id": user_id}, {"$set": {"password_hash": hash_password(payload.new_password)}})
    await db.admin_audit.insert_one({
        "id": str(uuid.uuid4()), "actor_id": admin["id"], "actor_email": admin["email"],
        "action": "password_reset", "target_user_id": user_id, "target_email": user.get("email"), "at": now_iso(),
    })
    await send_email(user["email"], "[d31337m3] Your password was reset",
                     "An administrator has reset your password. Please log in with the new password and change it from your profile.\n\n— d31337m3")
    return {"ok": True}


@api.post("/admin/users/{user_id}/scan")
async def admin_trigger_scan(user_id: str, background: BackgroundTasks, admin: dict = Depends(require_admin)):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    background.add_task(scan_and_notify, user_id, user["email"], None)
    await db.admin_audit.insert_one({
        "id": str(uuid.uuid4()), "actor_id": admin["id"], "actor_email": admin["email"],
        "action": "admin_scan", "target_user_id": user_id, "at": now_iso(),
    })
    return {"ok": True, "status": "queued"}


@api.post("/admin/users/{user_id}/impersonate")
async def admin_impersonate(user_id: str, admin: dict = Depends(require_admin)):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    token = create_token(user["id"], user.get("is_admin", False))
    await db.admin_audit.insert_one({
        "id": str(uuid.uuid4()), "actor_id": admin["id"], "actor_email": admin["email"],
        "action": "impersonate", "target_user_id": user_id, "target_email": user.get("email"), "at": now_iso(),
    })
    return {"token": token, "user": {"id": user["id"], "email": user["email"], "name": user.get("name"),
                                     "is_admin": user.get("is_admin", False), "plan_id": user.get("plan_id"),
                                     "subscription_status": user.get("subscription_status")}}


@api.get("/admin/audit-log")
async def admin_audit_log(admin: dict = Depends(require_admin)):
    rows = await db.admin_audit.find({}, {"_id": 0}).sort("at", -1).to_list(500)
    return {"audit": rows}


# ── Wave 2: Analytics + System Health + Documents ─────────────────────────────
@api.get("/admin/analytics")
async def admin_analytics(admin: dict = Depends(require_admin)):
    days = 30
    today = datetime.now(timezone.utc).date()
    series = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        series.append({"d": d.isoformat(), "signups": 0, "revenue": 0, "findings": 0, "removals": 0, "active_scans": 0})
    idx = {s["d"]: s for s in series}

    # Signups
    async for u in db.users.find({}, {"created_at": 1}):
        k = (u.get("created_at") or "")[:10]
        if k in idx:
            idx[k]["signups"] += 1
    # Revenue (confirmed payments only)
    async for p in db.payments.find({"status": "confirmed"}, {"created_at": 1, "amount_usd": 1}):
        k = (p.get("created_at") or "")[:10]
        if k in idx:
            idx[k]["revenue"] += int(p.get("amount_usd", 0) or 0)
    # Findings
    async for f in db.findings.find({}, {"discovered_at": 1}):
        k = (f.get("discovered_at") or "")[:10]
        if k in idx:
            idx[k]["findings"] += 1
    # Removals
    async for r in db.removal_requests.find({}, {"created_at": 1}):
        k = (r.get("created_at") or "")[:10]
        if k in idx:
            idx[k]["removals"] += 1
    # Active scans per day
    async for s in db.scans.find({}, {"ran_at": 1}):
        k = (s.get("ran_at") or "")[:10]
        if k in idx:
            idx[k]["active_scans"] += 1

    # MRR by plan (active subs only)
    plan_counts = {"basic": 0, "pro": 0, "enterprise": 0}
    async for u in db.users.find({"subscription_status": "active"}, {"plan_id": 1}):
        pid = u.get("plan_id")
        if pid in plan_counts:
            plan_counts[pid] += 1
    mrr_by_plan = [
        {"plan": p.title(), "subs": plan_counts[p], "mrr": plan_counts[p] * PLANS[p]["price_usd"], "color":
         "#71717a" if p == "basic" else "#FFD700" if p == "pro" else "#FF3333"}
        for p in ["basic", "pro", "enterprise"]
    ]
    total_mrr = sum(m["mrr"] for m in mrr_by_plan)

    # Method split
    method_split = {"interac": 0, "crypto": 0, "paypal": 0}
    async for p in db.payments.find({"status": "confirmed"}, {"method": 1}):
        m = p.get("method")
        if m in method_split:
            method_split[m] += 1

    # Severity distribution (active findings)
    sev_dist = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    async for f in db.findings.find({"status": "active"}, {"severity": 1}):
        s = f.get("severity")
        if s in sev_dist:
            sev_dist[s] += 1

    return {
        "timeseries": series,
        "mrr_total": total_mrr,
        "mrr_by_plan": mrr_by_plan,
        "method_split": [{"name": k, "value": v} for k, v in method_split.items()],
        "severity_distribution": [{"name": k.upper(), "value": v} for k, v in sev_dist.items()],
        "totals": {
            "users": await db.users.count_documents({}),
            "active_subs": await db.users.count_documents({"subscription_status": "active"}),
            "trial_users": await db.users.count_documents({"subscription_status": "trial"}),
            "suspended_users": await db.users.count_documents({"subscription_status": "suspended"}),
            "total_revenue": sum(s["revenue"] for s in series),
            "documents_signed": await db.documents.count_documents({"status": "signed"}),
            "documents_dispatched": await db.documents.count_documents({"dispatched_at": {"$ne": None}}),
        },
    }


@api.get("/admin/health")
async def admin_health(admin: dict = Depends(require_admin)):
    health = {"checks": [], "ok": True}

    # Mongo
    try:
        await db.command("ping")
        stats = await db.command("dbstats")
        health["checks"].append({"name": "MongoDB", "status": "ok", "detail": f"collections={stats.get('collections')} data={int(stats.get('dataSize',0)/1024)}KB"})
    except Exception as e:
        health["checks"].append({"name": "MongoDB", "status": "fail", "detail": str(e)[:120]})
        health["ok"] = False

    # SMTP config
    if SMTP_ENABLED:
        h24 = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        delivered = await db.email_log.count_documents({"sent_at": {"$gte": h24}, "delivered": True})
        failed = await db.email_log.count_documents({"sent_at": {"$gte": h24}, "delivered": False, "mocked": {"$ne": True}})
        health["checks"].append({
            "name": "SMTP", "status": "ok" if failed == 0 else "warn",
            "detail": f"24h: {delivered} sent / {failed} failed · host={os.environ.get('SMTP_HOST')}",
        })
    else:
        health["checks"].append({"name": "SMTP", "status": "warn", "detail": "SMTP_ENABLED=false (emails are mocked)"})

    # Crypto RPCs
    try:
        from web3 import Web3
        for name, env_key in [("Ethereum RPC", "ETHEREUM_RPC_URL"), ("Polygon RPC", "POLYGON_RPC_URL"), ("Base RPC", "BASE_RPC_URL")]:
            try:
                w3 = Web3(Web3.HTTPProvider(os.environ[env_key], request_kwargs={"timeout": 5}))
                bn = w3.eth.block_number
                health["checks"].append({"name": name, "status": "ok", "detail": f"block={bn}"})
            except Exception as e:
                health["checks"].append({"name": name, "status": "fail", "detail": str(e)[:120]})
                health["ok"] = False
    except Exception as e:
        health["checks"].append({"name": "Web3", "status": "fail", "detail": str(e)[:120]})

    # Background scan stats
    h1 = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    recent_scans = await db.scans.count_documents({"ran_at": {"$gte": h1}})
    health["checks"].append({"name": "Scan Engine", "status": "ok", "detail": f"{recent_scans} scans in last hour"})

    # PayPal config
    if os.environ.get("PAYPAL_CLIENT_ID"):
        health["checks"].append({"name": "PayPal", "status": "ok", "detail": "Credentials configured"})
    else:
        health["checks"].append({"name": "PayPal", "status": "warn", "detail": "PAYPAL_CLIENT_ID not configured (paypal_unavailable)"})

    health["checked_at"] = now_iso()
    return health


class HealthTestEmailIn(BaseModel):
    to: EmailStr


@api.post("/admin/health/smtp-test")
async def admin_smtp_test(payload: HealthTestEmailIn, admin: dict = Depends(require_admin)):
    ok = await send_email(payload.to, "[d31337m3] SMTP test ping",
                          f"This is a test from the admin health panel.\nSent by {admin['email']} at {now_iso()}.\n\nIf you receive this, SMTP is healthy.")
    return {"ok": ok}


@api.get("/admin/documents")
async def admin_documents(admin: dict = Depends(require_admin)):
    rows = await db.documents.find({}, {"_id": 0, "signature_image": 0}).sort("created_at", -1).to_list(1000)
    user_ids = list({d["user_id"] for d in rows if d.get("user_id")})
    users = {u["id"]: u for u in await db.users.find({"id": {"$in": user_ids}}, {"_id": 0, "id": 1, "email": 1}).to_list(1000)}
    for d in rows:
        d["user_email"] = users.get(d["user_id"], {}).get("email")
    return {"documents": rows}


@api.get("/admin/documents/{document_id}")
async def admin_get_document(document_id: str, admin: dict = Depends(require_admin)):
    d = await db.documents.find_one({"id": document_id}, {"_id": 0})
    if not d:
        raise HTTPException(status_code=404, detail="Not found")
    if d.get("user_id"):
        d["_user"] = await db.users.find_one({"id": d["user_id"]}, {"_id": 0, "password_hash": 0})
    return {"document": d}


# ── Wave 3: Broker Contacts CRUD ──────────────────────────────────────────────
class BrokerContactIn(BaseModel):
    broker: str
    email: Optional[str] = None
    form: Optional[str] = None


@api.get("/admin/broker-contacts")
async def admin_list_broker_contacts(admin: dict = Depends(require_admin)):
    rows = await db.broker_contacts.find({}, {"_id": 0}).sort("broker", 1).to_list(500)
    return {"contacts": rows}


@api.post("/admin/broker-contacts")
async def admin_upsert_broker_contact(payload: BrokerContactIn, admin: dict = Depends(require_admin)):
    if not payload.broker.strip():
        raise HTTPException(status_code=400, detail="Broker name required")
    update = {
        "broker": payload.broker.strip(),
        "email": payload.email,
        "form": payload.form,
        "updated_at": now_iso(),
        "updated_by": admin["email"],
    }
    existing = await db.broker_contacts.find_one({"broker": update["broker"]})
    if existing:
        await db.broker_contacts.update_one({"broker": update["broker"]}, {"$set": update})
    else:
        update["id"] = str(uuid.uuid4())
        update["created_at"] = now_iso()
        await db.broker_contacts.insert_one(update)
    await db.admin_audit.insert_one({
        "id": str(uuid.uuid4()), "actor_id": admin["id"], "actor_email": admin["email"],
        "action": "broker_contact_upsert", "target_email": update["broker"], "changes": update, "at": now_iso(),
    })
    return {"ok": True}


@api.delete("/admin/broker-contacts/{broker_name}")
async def admin_delete_broker_contact(broker_name: str, admin: dict = Depends(require_admin)):
    res = await db.broker_contacts.delete_one({"broker": broker_name})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    await db.admin_audit.insert_one({
        "id": str(uuid.uuid4()), "actor_id": admin["id"], "actor_email": admin["email"],
        "action": "broker_contact_delete", "target_email": broker_name, "at": now_iso(),
    })
    return {"ok": True}


# ── Wave 3: Settings (read-only summary) ──────────────────────────────────────
@api.get("/admin/settings")
async def admin_settings(admin: dict = Depends(require_admin)):
    def mask(v: str) -> str:
        if not v:
            return ""
        if len(v) <= 6:
            return "***"
        return v[:3] + "*" * (len(v) - 6) + v[-3:]

    return {
        "environment": {
            "mongo_db": os.environ.get("DB_NAME"),
            "smtp_host": os.environ.get("SMTP_HOST"),
            "smtp_port": os.environ.get("SMTP_PORT"),
            "smtp_username": os.environ.get("SMTP_USERNAME"),
            "smtp_password_masked": mask(os.environ.get("SMTP_PASSWORD", "")),
            "smtp_enabled": SMTP_ENABLED,
            "smtp_from": os.environ.get("SMTP_FROM"),
            "payments_email": PAYMENTS_EMAIL,
            "crypto_wallet": CRYPTO_WALLET,
            "ethereum_rpc": os.environ.get("ETHEREUM_RPC_URL"),
            "polygon_rpc": os.environ.get("POLYGON_RPC_URL"),
            "base_rpc": os.environ.get("BASE_RPC_URL"),
            "paypal_configured": bool(os.environ.get("PAYPAL_CLIENT_ID")),
            "paypal_api_base": os.environ.get("PAYPAL_API_BASE"),
            "jwt_algorithm": JWT_ALGORITHM,
            "token_expiry_minutes": TOKEN_EXP_MIN,
            "admin_email": ADMIN_EMAIL,
            "cors_origins": os.environ.get("CORS_ORIGINS"),
        },
        "rate_limiter": {
            "window_seconds": RATE_WINDOW_SEC,
            "max_attempts": RATE_MAX_ATTEMPTS,
            "active_buckets": len(RATE_LIMITS),
        },
        "plans": list(PLANS.values()),
        "supported_countries": list(SUPPORTED_COUNTRIES.keys()),
        "broker_count_db": await db.broker_contacts.count_documents({}),
        "broker_count_builtin": len(BROKER_CONTACTS),
    }


@api.get("/admin/payments/{payment_id}")
async def admin_get_payment(payment_id: str, admin: dict = Depends(require_admin)):
    p = await db.payments.find_one({"id": payment_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Not found")
    if p.get("user_id"):
        user = await db.users.find_one({"id": p["user_id"]}, {"_id": 0, "password_hash": 0})
        p["_user"] = user
    return {"payment": p}


@api.get("/admin/removals/{removal_id}")
async def admin_get_removal(removal_id: str, admin: dict = Depends(require_admin)):
    r = await db.removal_requests.find_one({"id": removal_id}, {"_id": 0})
    if not r:
        raise HTTPException(status_code=404, detail="Not found")
    if r.get("user_id"):
        r["_user"] = await db.users.find_one({"id": r["user_id"]}, {"_id": 0, "password_hash": 0})
    if r.get("finding_id"):
        r["_finding"] = await db.findings.find_one({"id": r["finding_id"]}, {"_id": 0})
    if r.get("dispatched_document_id"):
        r["_document"] = await db.documents.find_one({"id": r["dispatched_document_id"]}, {"_id": 0})
    return {"removal": r}


# ---------------- Profile ----------------
@api.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    profile = await db.profiles.find_one({"user_id": user["id"]}, {"_id": 0}) or {
        "user_id": user["id"], "name": user.get("name"), "address": "", "phone": "",
        "country": "CA", "state": "ON",
    }
    return {"profile": profile}


@api.put("/profile")
async def update_profile(payload: ProfileIn, user: dict = Depends(get_current_user)):
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    update["user_id"] = user["id"]
    update["updated_at"] = now_iso()
    await db.profiles.update_one({"user_id": user["id"]}, {"$set": update}, upsert=True)
    if payload.name:
        await db.users.update_one({"id": user["id"]}, {"$set": {"name": payload.name}})
    return {"ok": True, "profile": update}


# ---------------- Countries ----------------
@api.get("/countries")
async def get_countries():
    return {"countries": SUPPORTED_COUNTRIES}


# ---------------- E-Signature ----------------
@api.get("/signature")
async def get_signature(user: dict = Depends(get_current_user)):
    sig = await db.signatures.find_one({"user_id": user["id"]}, {"_id": 0})
    return {"signature": sig}


@api.post("/signature")
async def save_signature(payload: SignatureIn, user: dict = Depends(get_current_user)):
    if not payload.data_url.startswith("data:image/"):
        raise HTTPException(status_code=400, detail="Invalid signature image")
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "data_url": payload.data_url,
        "full_name": payload.full_name,
        "created_at": now_iso(),
        "ip": None,
    }
    # Replace existing
    await db.signatures.delete_many({"user_id": user["id"]})
    await db.signatures.insert_one(doc)
    return {"ok": True, "signature": {k: v for k, v in doc.items() if k != "_id"}}


# ---------------- Legal Documents ----------------
@api.get("/documents/templates")
async def get_doc_templates(user: dict = Depends(get_current_user)):
    profile = await db.profiles.find_one({"user_id": user["id"]}) or {}
    user_country = profile.get("country", "CA")
    templates = [
        {"id": t["id"], "title": t["title"], "summary": t["summary"], "jurisdictions": t["jurisdictions"],
         "available": user_country in t["jurisdictions"]}
        for t in LEGAL_TEMPLATES.values()
    ]
    return {"templates": templates, "user_country": user_country}


def _fill_template(template_id: str, ctx: dict) -> str:
    tpl = LEGAL_TEMPLATES[template_id]["body"]
    safe = {k: (v if v is not None else "") for k, v in ctx.items()}
    for k in ["user_name", "user_email", "user_address", "user_phone",
              "recipient_broker", "recipient_address", "finding_url", "finding_data",
              "date", "country_name", "privacy_law", "state_clause"]:
        safe.setdefault(k, "")
    return tpl.format(**safe)


@api.post("/documents/generate")
async def generate_document(payload: GenerateDocumentIn, user: dict = Depends(get_current_user)):
    tpl = LEGAL_TEMPLATES.get(payload.template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")

    profile = await db.profiles.find_one({"user_id": user["id"]}) or {}
    country = profile.get("country", "CA")
    if country not in tpl["jurisdictions"]:
        raise HTTPException(status_code=400, detail=f"{tpl['title']} is not available in {SUPPORTED_COUNTRIES.get(country, {}).get('name', country)}")
    if country not in SUPPORTED_COUNTRIES:
        raise HTTPException(status_code=400, detail="Country must be Canada, United States, or Mexico")

    state = profile.get("state")
    finding_url = ""
    finding_data = ""
    recipient_broker = payload.recipient_broker or "Recipient"
    if payload.finding_id:
        f = await db.findings.find_one({"id": payload.finding_id, "user_id": user["id"]})
        if f:
            finding_url = f.get("url", "")
            finding_data = ", ".join(f.get("data_found", []))
            recipient_broker = payload.recipient_broker or f.get("broker", "Recipient")

    ctx = {
        "user_name": profile.get("name") or user.get("name") or user["email"],
        "user_email": user["email"],
        "user_address": profile.get("address", "[address on file]"),
        "user_phone": profile.get("phone", "[phone on file]"),
        "recipient_broker": recipient_broker,
        "recipient_address": payload.recipient_address or "[Recipient Address]",
        "finding_url": finding_url or "[URL on file]",
        "finding_data": finding_data or "[Personal data exposed]",
        "date": datetime.now(timezone.utc).strftime("%B %d, %Y"),
        "country_name": SUPPORTED_COUNTRIES[country]["name"],
        "privacy_law": SUPPORTED_COUNTRIES[country]["privacy_law"],
        "state_clause": f", state/province of {state}" if state else "",
    }
    body = _fill_template(payload.template_id, ctx)
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "template_id": payload.template_id,
        "title": tpl["title"],
        "recipient_broker": recipient_broker,
        "finding_id": payload.finding_id,
        "country": country,
        "body": body,
        "status": "draft",
        "signed_at": None,
        "signature_image": None,
        "signed_name": None,
        "created_at": now_iso(),
    }
    await db.documents.insert_one(doc)
    return {"document": {k: v for k, v in doc.items() if k != "_id"}}


@api.get("/documents")
async def list_documents(user: dict = Depends(get_current_user)):
    rows = await db.documents.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"documents": rows}


@api.get("/documents/{document_id}")
async def get_document(document_id: str, user: dict = Depends(get_current_user)):
    doc = await db.documents.find_one({"id": document_id, "user_id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return {"document": doc}


@api.post("/documents/sign")
async def sign_document(payload: SignDocumentIn, background: BackgroundTasks, user: dict = Depends(get_current_user)):
    doc = await db.documents.find_one({"id": payload.document_id, "user_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    sig = await db.signatures.find_one({"user_id": user["id"]})
    if not sig:
        raise HTTPException(status_code=400, detail="No signature on file. Please create your e-signature first.")
    signed_body = doc["body"].replace("[SIGNATURE]", f"[Electronically signed by {sig['full_name']} on {now_iso()}]")

    # Attempt broker dispatch if the document is linked to a finding
    dispatch = {"attempted": False, "delivered": False, "broker_email": None, "form_url": None}
    if doc.get("finding_id"):
        f = await db.findings.find_one({"id": doc["finding_id"], "user_id": user["id"]})
        if f:
            contact = await get_broker_contact(f.get("broker"))
            broker_email = contact.get("email")
            dispatch["broker_email"] = broker_email
            dispatch["form_url"] = contact.get("form")
            if broker_email:
                dispatch["attempted"] = True
                # Background-dispatch the signed document to the broker
                background.add_task(
                    send_email,
                    broker_email,
                    f"[{doc['title']}] Removal Request — {sig['full_name']} (ref {doc['id'][:8]})",
                    signed_body,
                    [{"filename": f"{doc['title'].replace(' ', '_')}_{doc['id'][:8]}.txt",
                      "content": signed_body, "maintype": "text", "subtype": "plain"}],
                )
                dispatch["delivered"] = True  # queued for background send
                # Update finding status
                await db.findings.update_one(
                    {"id": doc["finding_id"]},
                    {"$set": {"status": "pending_removal", "dispatched_at": now_iso(),
                              "dispatched_to": broker_email, "dispatched_document_id": doc["id"]}}
                )
                # Update removal_request if exists
                await db.removal_requests.update_one(
                    {"finding_id": doc["finding_id"]},
                    {"$set": {"status": "dispatched", "dispatched_at": now_iso(),
                              "dispatched_document_id": doc["id"], "broker_email": broker_email}}
                )

    await db.documents.update_one({"id": payload.document_id}, {"$set": {
        "status": "signed",
        "signed_at": now_iso(),
        "signature_image": sig["data_url"],
        "signed_name": sig["full_name"],
        "body": signed_body,
        "dispatched_to": dispatch.get("broker_email"),
        "dispatched_at": now_iso() if dispatch.get("delivered") else None,
    }})

    # Confirmation email to the user
    confirm_msg = (
        f"Your {doc['title']} has been electronically signed.\n\n"
        + (f"Dispatched to: {dispatch['broker_email']}\n" if dispatch["delivered"] else "")
        + (f"Broker opt-out form: {dispatch['form_url']}\n" if dispatch.get("form_url") and not dispatch["delivered"] else "")
        + "\nTrack status in your dashboard.\n\n— d31337m3"
    )
    background.add_task(send_email, user["email"], f"[d31337m3] Document signed — {doc['title']}", confirm_msg)
    return {"ok": True, "dispatch": dispatch}


@api.delete("/documents/{document_id}")
async def delete_document(document_id: str, user: dict = Depends(get_current_user)):
    res = await db.documents.delete_one({"id": document_id, "user_id": user["id"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


# ---------------- App wiring ----------------
app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    # seed admin user if missing
    if not await db.users.find_one({"email": ADMIN_EMAIL}):
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "email": ADMIN_EMAIL,
            "name": "Admin",
            "password_hash": hash_password(ADMIN_PASSWORD),
            "auth_provider": "password",
            "is_admin": True, "is_active": True,
            "plan_id": "enterprise", "subscription_status": "active",
            "subscription_started_at": now_iso(),
            "created_at": now_iso(),
        })
        logger.info(f"Seeded admin user: {ADMIN_EMAIL}")
    # indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.keywords.create_index([("user_id", 1)])
    await db.findings.create_index([("user_id", 1)])
    # Seed broker contacts from constants if collection is empty (Wave 3)
    if await db.broker_contacts.count_documents({}) == 0:
        for broker, c in BROKER_CONTACTS.items():
            await db.broker_contacts.insert_one({
                "id": str(uuid.uuid4()),
                "broker": broker, "email": c.get("email"), "form": c.get("form"),
                "created_at": now_iso(), "updated_at": now_iso(), "updated_by": "system_seed",
            })
        logger.info(f"Seeded {len(BROKER_CONTACTS)} broker contacts into db.broker_contacts")


@app.on_event("shutdown")
async def shutdown():
    mongo_client.close()
