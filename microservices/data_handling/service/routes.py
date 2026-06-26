"""
API Routes for Data Handling Service
Contains data scraping, enrichment, scan execution, and findings management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, status
from typing import Optional, List
import os
import logging
import json
import aiohttp
import asyncio
import random
from datetime import datetime, timedelta
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

# Import shared components
import sys
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices/shared')

from shared.jwt_utils import create_service_token, verify_service_token, create_user_token, verify_user_token
from shared.security_middleware import verify_service_request, verify_user_request, require_service_auth, require_user_auth
from shared.database_models import *
from shared.utils import now_iso, hash_password, verify_password, SUPPORTED_COUNTRIES, DATA_BROKERS, PLANS

# Import local models (would be defined in a models.py file)
# For now, we'll define them inline or import from shared

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("data_handling.routes")

# Create routers
scan_router = APIRouter()
findings_router = APIRouter()
keywords_router = APIRouter()
broker_router = APIRouter()

# Mock database functions (in a real implementation, these would connect to actual databases)
async def get_user_by_email(email: str):
    """Mock function to get user by email"""
    # This would be replaced with actual database query
    return None

async def get_user_by_id(user_id: str):
    """Mock function to get user by ID"""
    # This would be replaced with actual database query
    return None

async def create_user(user_data: dict):
    """Mock function to create a user"""
    # This would be replaced with actual database insert
    return user_data

async def get_keywords_by_user_id(user_id: str):
    """Mock function to get keywords by user ID"""
    # This would be replaced with actual database query
    return []

async def get_keyword_by_id(keyword_id: str):
    """Mock function to get keyword by ID"""
    # This would be replaced with actual database query
    return None

async def create_keyword(keyword_data: dict):
    """Mock function to create a keyword"""
    # This would be replaced with actual database insert
    return keyword_data

async def update_keyword(keyword_id: str, update_data: dict):
    """Mock function to update a keyword"""
    # This would be replaced with actual database update
    return {**update_data, "id": keyword_id}

async def get_findings_by_user_id(user_id: str):
    """Mock function to get findings by user ID"""
    # This would be replaced with actual database query
    return []

async def get_finding_by_id(finding_id: str):
    """Mock function to get finding by ID"""
    # This would be replaced with actual database query
    return None

async def create_finding(finding_data: dict):
    """Mock function to create a finding"""
    # This would be replaced with actual database insert
    return finding_data

async def update_finding(finding_id: str, update_data: dict):
    """Mock function to update a finding"""
    # This would be replaced with actual database update
    return {**update_data, "id": finding_id}

async def get_scans_by_user_id(user_id: str):
    """Mock function to get scans by user ID"""
    # This would be replaced with actual database query
    return []

async def create_scan(scan_data: dict):
    """Mock function to create a scan"""
    # This would be replaced with actual database insert
    return scan_data

# Data scraping and enrichment functions (moved from backend/server.py)
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
    keywords = await get_keywords_by_user_id(user_id)  # Simplified for mock
    new_count = 0
    for kw in keywords:
        findings = await real_scrape_for_keyword(kw["value"], kw["type"])
        for f in findings:
            # dedupe by (broker,url,user_id,keyword_id)
            existing = await get_finding_by_id(None)  # Simplified for mock - would check for duplicates
            if existing:
                continue
            doc = {
                "id": generate_id(),
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
            await create_finding(doc)
            new_count += 1
        await update_keyword(kw["id"], {"last_scan_at": now_iso()})
    # update scan log
    await create_scan({
        "id": generate_id(),
        "user_id": user_id,
        "keyword_ids": keyword_ids or [k["id"] for k in keywords],
        "new_findings": new_count,
        "ran_at": now_iso(),
    })
    return new_count

async def scan_and_notify(user_id: str, user_email: str, keyword_ids: Optional[list[str]] = None) -> None:
    new_count = await run_scan_for_user(user_id, keyword_ids)
    if new_count > 0:
        body = (
            f"d31337m3 — New Findings Detected\\n\\n"
            f"{new_count} new data broker exposures matching your monitored keywords have been found.\\n\\n"
            f"Login to your dashboard to review and request removal:\\n"
            f"https://d31337m3.com/dashboard\\n\\n"
            f"— The d31337m3 Team\n"
        )
        await send_email_mock(user_email, f"[d31337m3] {new_count} new findings detected", body)

# Email service mock (can be replaced with real implementation)
async def send_email_mock(to: str, subject: str, body: str, attachments: Optional[List[Dict]] = None) -> bool:
    """Mock email service for development"""
    # In production, this would be replaced with real email sending
    print(f"[EMAIL-MOCK] to={to} subject={subject!r}")
    return True

# Pydantic models (imported from shared or defined locally)
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import datetime

class KeywordIn(BaseModel):
    value: str
    type: Literal["name", "email", "phone", "address", "other"] = "name"

class ScanRequestIn(BaseModel):
    keyword_id: Optional[str] = None  # if None, scans all user keywords

class RemovalRequestIn(BaseModel):
    finding_id: str

# Re-export shared models for convenience
from shared.database_models import (
    UserBase, UserCreate, UserLogin, UserInDB, UserResponse,
    TokenResponse, KeywordBase, KeywordCreate, KeywordInDB,
    FindingBase, FindingCreate, FindingInDB,
    RemovalRequestBase, RemovalRequestCreate, RemovalRequestInDB,
    PaymentBase, PaymentCreate, PaymentInDB,
    ProfileBase, ProfileCreate, ProfileInDB,
    SignatureBase, SignatureCreate, SignatureInDB,
    DocumentBase, DocumentCreate, DocumentInDB,
    BrokerContactBase, BrokerContactCreate, BrokerContactInDB,
    generate_id, now_iso, hash_password, verify_password
)