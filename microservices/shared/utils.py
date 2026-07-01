"""
Shared utility functions for microservices
Contains common helper functions used across services
"""

import re
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from urllib.parse import quote_plus

from .database_models import hash_password, verify_password
from .secrets_manager import get_secret, get_int_secret

# Common utility functions

def generate_id() -> str:
    """Generate a unique ID"""
    return str(uuid.uuid4())

def now_iso() -> str:
    """Get current timestamp in ISO format"""
    return datetime.now(timezone.utc).isoformat()

def parse_promo_expires(value: Optional[str]) -> Optional[datetime]:
    """Parse promo expiration date"""
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
    """Normalize promo code to uppercase"""
    return value.strip().upper()

def build_promo_code(code: str, percent: int, expires: str) -> Optional[dict]:
    """Build a promo code dictionary"""
    if not code or not code.strip():
        return None
    expires_at = parse_promo_expires(expires)
    return {
        "code": normalize_promo_code(code),
        "percent_off": int(percent),
        "expires_at": expires_at,
        "expires_raw": expires.strip(),
    }

def find_promo_for_code(code: str, promo_list: List[dict]) -> Optional[dict]:
    """Find a promo code in a list"""
    normalized = normalize_promo_code(code)
    for promo in promo_list:
        if promo["code"] == normalized:
            return promo
    return None

def promo_is_expired(promo: dict) -> bool:
    """Check if a promo code is expired"""
    if not promo.get("expires_at"):
        return False
    return promo["expires_at"].date() < datetime.now(timezone.utc).date()

# Supported countries data (shared across services)
SUPPORTED_COUNTRIES = {
    "CA": {"name": "Canada", "states": ["AB","BC","MB","NB","NL","NS","NT","NU","ON","PE","QC","SK","YT"], "privacy_law": "PIPEDA / Quebec Law 25"},
    "US": {"name": "United States", "states": ["AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC"], "privacy_law": "CCPA / CPRA / State Privacy Laws"},
    "MX": {"name": "México", "states": ["AGU","BCN","BCS","CAM","CHP","CHH","COA","COL","CMX","DUR","GUA","GRO","HID","JAL","MEX","MIC","MOR","NAY","NLE","OAX","PUE","QUE","ROO","SLP","SIN","SON","TAB","TAM","TLA","VER","YUC","ZAC"], "privacy_law": "LFPDPPP"},
}

# Data brokers list (shared across services)
BROKER_DIRECTORY = [
    {
        "name": "Acxiom",
        "region": "USA/Global",
        "privacy_email": "privacy@acxiom.com",
        "privacy_phone": "1-877-774-2099",
        "address": "301 E. Dave Ward Dr., Conway, AR 72032",
        "opt_out_url": "https://www.acxiom.com/opt-out/",
        "aliases": [],
    },
    {
        "name": "Experian",
        "region": "USA/Global",
        "privacy_email": "optout@experian.com",
        "privacy_phone": "1-888-397-3742",
        "address": "475 Anton Blvd, Costa Mesa, CA 92626",
        "opt_out_url": "https://www.experian.com/privacy/opt-out-target-advertising",
        "aliases": [],
    },
    {
        "name": "LexisNexis",
        "region": "USA/Global",
        "privacy_email": "privacy.policy@lexisnexis.com",
        "privacy_phone": "1-800-833-9848",
        "address": "9443 Springboro Pike, Miamisburg, OH 45342",
        "opt_out_url": "https://optout.lexisnexis.com/",
        "aliases": [],
    },
    {
        "name": "Whitepages",
        "region": "USA",
        "privacy_email": "privacy@whitepages.com",
        "privacy_phone": "1-800-952-8800",
        "address": "2033 6th Ave #1600, Seattle, WA 98121",
        "opt_out_url": "https://www.whitepages.com/name/{first_name}-{last_name}",
        "aliases": ["WhitePages"],
    },
    {
        "name": "Spokeo",
        "region": "USA",
        "privacy_email": "privacy@spokeo.com",
        "privacy_phone": "1-888-271-3321",
        "address": "556 S. Fair Oaks Ave, Pasadena, CA 91105",
        "opt_out_url": "https://www.spokeo.com/{first_name}-{last_name}",
        "aliases": [],
    },
    {
        "name": "BeenVerified",
        "region": "USA",
        "privacy_email": "privacy@beenverified.com",
        "privacy_phone": "1-866-885-6480",
        "address": "19 Union Sq W, New York, NY 10003",
        "opt_out_url": "https://www.beenverified.com/f/optout/search",
        "aliases": [],
    },
    {
        "name": "Radaris",
        "region": "USA",
        "privacy_email": "privacy@radaris.com",
        "privacy_phone": "1-855-723-2747",
        "address": "P.O. Box 425510, Cambridge, MA 02142",
        "opt_out_url": "https://radaris.com/p/{first_name}/{last_name}",
        "aliases": [],
    },
    {
        "name": "PeopleFinders",
        "region": "USA",
        "privacy_email": "privacy@peoplefinders.com",
        "privacy_phone": "1-800-718-8997",
        "address": "1821 Q St, Sacramento, CA 95811",
        "opt_out_url": "https://www.peoplefinders.com/find/person/{first_name}-{last_name}",
        "aliases": ["PeopleFinder"],
    },
    {
        "name": "Intelius",
        "region": "USA",
        "privacy_email": "privacy@intelius.com",
        "privacy_phone": "1-888-245-1655",
        "address": "10900 NE 4th St, Bellevue, WA 98004",
        "opt_out_url": "https://www.intelius.com/people-search/{first_name}-{last_name}",
        "aliases": [],
    },
    {
        "name": "LocateFamily",
        "region": "USA/Canada/Global",
        "privacy_email": "privacy@locatefamily.com",
        "privacy_phone": "N/A",
        "address": "Online Registry Only",
        "opt_out_url": "https://www.locatefamily.com/Street-Lists/index.html",
        "aliases": [],
    },
    {
        "name": "MyLife",
        "region": "USA",
        "privacy_email": None,
        "privacy_phone": None,
        "address": None,
        "opt_out_url": None,
        "aliases": [],
    },
    {
        "name": "TruthFinder",
        "region": "USA",
        "privacy_email": None,
        "privacy_phone": None,
        "address": None,
        "opt_out_url": None,
        "aliases": [],
    },
    {
        "name": "FastPeopleSearch",
        "region": "USA",
        "privacy_email": None,
        "privacy_phone": None,
        "address": None,
        "opt_out_url": None,
        "aliases": [],
    },
    {
        "name": "PublicRecords",
        "region": "USA",
        "privacy_email": None,
        "privacy_phone": None,
        "address": None,
        "opt_out_url": None,
        "aliases": [],
    },
    {
        "name": "Equifax",
        "region": "USA/Global",
        "privacy_email": None,
        "privacy_phone": None,
        "address": None,
        "opt_out_url": None,
        "aliases": ["Equifax-PrivacyData"],
    },
    {
        "name": "PeekYou",
        "region": "USA",
        "privacy_email": None,
        "privacy_phone": None,
        "address": None,
        "opt_out_url": None,
        "aliases": [],
    },
    {
        "name": "InstantCheckmate",
        "region": "USA",
        "privacy_email": None,
        "privacy_phone": None,
        "address": None,
        "opt_out_url": None,
        "aliases": [],
    },
    {
        "name": "USSearch",
        "region": "USA",
        "privacy_email": None,
        "privacy_phone": None,
        "address": None,
        "opt_out_url": None,
        "aliases": [],
    },
]

DATA_BROKERS = [entry["name"] for entry in BROKER_DIRECTORY]

DATA_BROKER_LOOKUP = {entry["name"]: entry for entry in BROKER_DIRECTORY}

for _broker_entry in BROKER_DIRECTORY:
    for _alias in _broker_entry.get("aliases", []):
        DATA_BROKER_LOOKUP[_alias] = _broker_entry

SEARCH_ENGINE_DIRECTORY = [
    {
        "name": "Google",
        "classification": "Popular",
        "privacy_email": "data-protection-office@google.com",
        "privacy_phone": "1-650-253-0000",
        "address": "1600 Amphitheatre Pkwy, Mountain View, CA 94043",
        "search_url": "https://www.google.com/search?q={query}",
    },
    {
        "name": "Bing",
        "classification": "Popular",
        "privacy_email": "msnhlp@microsoft.com",
        "privacy_phone": "1-800-642-7676",
        "address": "One Microsoft Way, Redmond, WA 98052",
        "search_url": "https://www.bing.com/search?q={query}",
    },
    {
        "name": "Yahoo Search",
        "classification": "Popular",
        "privacy_email": "privacypolicy@yahooinc.com",
        "privacy_phone": "1-800-318-0612",
        "address": "701 First Avenue, Sunnyvale, CA 94089",
        "search_url": "https://search.yahoo.com/search?p={query}",
    },
    {
        "name": "DuckDuckGo",
        "classification": "Popular",
        "privacy_email": "privacy@duckduckgo.com",
        "privacy_phone": "N/A",
        "address": "20 Paoli Pike, Paoli, PA 19301",
        "search_url": "https://duckduckgo.com/?q={query}",
    },
    {
        "name": "Mojeek",
        "classification": "Not Popular",
        "privacy_email": "privacy@mojeek.com",
        "privacy_phone": "+44 1273 006020",
        "address": "18 North Street, Brighton, BN1 1EB, UK",
        "search_url": "https://www.mojeek.com/search?q={query}",
    },
    {
        "name": "Gigablast",
        "classification": "Not Popular",
        "privacy_email": "privacy@gigablast.com",
        "privacy_phone": "N/A",
        "address": "New Mexico, USA",
        "search_url": "https://www.gigablast.com/search?q={query}",
    },
    {
        "name": "Exalead",
        "classification": "Not Popular",
        "privacy_email": "privacy@3ds.com",
        "privacy_phone": "+33 1 61 62 61 62",
        "address": "10 Rue Marcel Dassault, Vélizy-Villacoublay, France",
        "search_url": "https://www.exalead.com/search/web/results/?q={query}",
    },
    {
        "name": "Swisscows",
        "classification": "Not Popular",
        "privacy_email": "info@swisscows.com",
        "privacy_phone": "+41 71 454 70 10",
        "address": "Haldenstrasse 5, 9200 Gossau, Switzerland",
        "search_url": "https://swisscows.com/web?query={query}",
    },
]

SEARCH_ENGINES = [entry["name"] for entry in SEARCH_ENGINE_DIRECTORY]
SEARCH_ENGINE_LOOKUP = {entry["name"]: entry for entry in SEARCH_ENGINE_DIRECTORY}

# Plans and payment config shared across services.
PLANS = {
    "basic": {
        "id": "basic",
        "name": "Basic",
        "price_usd": 29,
        "keyword_limit": 5,
        "scan_freq": "weekly",
    },
    "pro": {
        "id": "pro",
        "name": "Pro",
        "price_usd": 79,
        "keyword_limit": 25,
        "scan_freq": "daily",
    },
    "enterprise": {
        "id": "enterprise",
        "name": "Enterprise",
        "price_usd": 199,
        "keyword_limit": 999,
        "scan_freq": "realtime",
    },
}

CRYPTO_WALLET = get_secret("CRYPTO_WALLET", "")
PAYMENTS_EMAIL = get_secret("PAYMENTS_EMAIL", "payments@example.com")


async def verify_usdc_tx(network: str, tx_hash: str, expected_amount_usd: float) -> Optional[dict]:
    """Placeholder verifier for USDC transactions.

    In production this should query on-chain providers and validate token, recipient,
    amount, and confirmation depth.
    """
    if not network or not tx_hash:
        return None
    return {
        "network": network,
        "tx_hash": tx_hash,
        "amount_usd": expected_amount_usd,
        "verified_at": now_iso(),
        "verification_mode": "placeholder",
    }

# Legal document templates (shared across services)
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
{date}""",
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

This letter serves as formal demand that {recipient_broker} (the \"Company\") immediately CEASE AND DESIST from the collection, publication, distribution, sale, or any further processing of the personal information of {user_name} (the \"Data Subject\").

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
{user_email}""",
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

{date}""",
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
{date}""",
    },
}

def _fill_template(template_id: str, ctx: dict) -> str:
    """Fill a legal template with context"""
    tpl = LEGAL_TEMPLATES[template_id]["body"]
    safe = {k: (v if v is not None else "") for k, v in ctx.items()}
    for k in ["user_name", "user_email", "user_address", "user_phone",
              "recipient_broker", "recipient_address", "finding_url", "finding_data",
              "date", "country_name", "privacy_law", "state_clause"]:
        safe.setdefault(k, "")
    return tpl.format(**safe)

# Email service mock (can be replaced with real implementation)
async def send_email_mock(to: str, subject: str, body: str, attachments: Optional[List[Dict]] = None) -> bool:
    """Mock email service for development"""
    # In production, this would be replaced with real email sending
    print(f"[EMAIL-MOCK] to={to} subject={subject!r}")
    return True

# Rate limiting utilities (shared)
RATE_LIMITS: Dict[str, List[float]] = {}
RATE_WINDOW_SEC = 60 * 15  # 15 minutes
RATE_MAX_ATTEMPTS = 8
RATE_LIMIT_MAX_KEYS = get_int_secret("RATE_LIMIT_MAX_KEYS", 50000)

def _ratelimit(key: str) -> tuple[bool, int]:
    """Return (allowed, retry_after_seconds)"""
    import time as _t
    now = _t.time()
    if len(RATE_LIMITS) > RATE_LIMIT_MAX_KEYS:
        # Drop empty buckets first; if still too large, drop oldest active buckets.
        for k in list(RATE_LIMITS.keys()):
            if not RATE_LIMITS.get(k):
                RATE_LIMITS.pop(k, None)
        if len(RATE_LIMITS) > RATE_LIMIT_MAX_KEYS:
            oldest = sorted(
                RATE_LIMITS.items(),
                key=lambda kv: kv[1][0] if kv[1] else now,
            )
            for k, _ in oldest[: max(1, len(RATE_LIMITS) - RATE_LIMIT_MAX_KEYS)]:
                RATE_LIMITS.pop(k, None)

    bucket = [t for t in RATE_LIMITS.get(key, []) if now - t < RATE_WINDOW_SEC]
    if not bucket and key in RATE_LIMITS:
        RATE_LIMITS.pop(key, None)
        bucket = []
    if len(bucket) >= RATE_MAX_ATTEMPTS:
        oldest = bucket[0]
        return False, int(RATE_WINDOW_SEC - (now - oldest))
    bucket.append(now)
    RATE_LIMITS[key] = bucket
    return True, 0