"""
Shared utility functions for microservices
Contains common helper functions used across services
"""

import os
import re
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from urllib.parse import quote_plus

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
DATA_BROKERS = [
    "Spokeo", "BeenVerified", "WhitePages", "Intelius", "MyLife",
    "Radaris", "PeopleFinder", "TruthFinder", "FastPeopleSearch",
    "PublicRecords", "Acxiom", "Equifax-PrivacyData", "PeekYou",
    "InstantCheckmate", "USSearch",
]

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

def _ratelimit(key: str) -> tuple[bool, int]:
    """Return (allowed, retry_after_seconds)"""
    import time as _t
    now = _t.time()
    bucket = [t for t in RATE_LIMITS.get(key, []) if now - t < RATE_WINDOW_SEC]
    if len(bucket) >= RATE_MAX_ATTEMPTS:
        oldest = bucket[0]
        return False, int(RATE_WINDOW_SEC - (now - oldest))
    bucket.append(now)
    RATE_LIMITS[key] = bucket
    return True, 0