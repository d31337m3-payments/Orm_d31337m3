"""
API Routes for Auditor Service
Contains audit trail recording and compliance reporting endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from typing import Optional, List
import os
import logging
import sqlite3
import json
import csv
import io
import threading
from datetime import datetime, timedelta, timezone

# Import shared components
import sys
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices/shared')

from shared.jwt_utils import create_service_token, verify_service_token, create_user_token, verify_user_token
from shared.security_middleware import verify_service_request, verify_user_request, require_service_auth, require_user_auth
from shared.database_models import *
from shared.utils import now_iso, hash_password, verify_password, SUPPORTED_COUNTRIES
from shared.secrets_manager import get_secret

# Import local models (would be defined in a models.py file)
# For now, we'll define them inline or import from shared

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("auditor.routes")

# Create routers
audit_router = APIRouter()
compliance_router = APIRouter()

AUDIT_ENTRIES: List[dict] = []
_db_lock = threading.Lock()


def _max_audit_entries() -> int:
    return int(get_secret("AUDITOR_MAX_ENTRIES", os.environ.get("AUDITOR_MAX_ENTRIES", "200000")) or "200000")


def _db_path() -> str:
    return get_secret("AUDITOR_DB_PATH", os.environ.get("AUDITOR_DB_PATH", "/tmp/d31337m3_auditor.db")) or "/tmp/d31337m3_auditor.db"


def _db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _db_lock:
        conn = _db_conn()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_entries (
                    id TEXT PRIMARY KEY,
                    actor_id TEXT,
                    actor_email TEXT,
                    action TEXT,
                    target_user_id TEXT,
                    target_email TEXT,
                    at TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_at ON audit_entries(at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_entries(actor_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_entries(action)")
            conn.commit()
        finally:
            conn.close()


def _persist_audit_entry(audit_data: dict) -> None:
    with _db_lock:
        conn = _db_conn()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO audit_entries
                (id, actor_id, actor_email, action, target_user_id, target_email, at, ip_address, user_agent, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_data.get("id"),
                    audit_data.get("actor_id"),
                    audit_data.get("actor_email"),
                    audit_data.get("action"),
                    audit_data.get("target_user_id"),
                    audit_data.get("target_email"),
                    audit_data.get("at"),
                    audit_data.get("ip_address"),
                    audit_data.get("user_agent"),
                    json.dumps(audit_data),
                ),
            )
            conn.execute(
                """
                DELETE FROM audit_entries
                WHERE id IN (
                    SELECT id FROM audit_entries
                    ORDER BY at DESC
                    LIMIT -1 OFFSET ?
                )
                """,
                (_max_audit_entries(),),
            )
            conn.commit()
        finally:
            conn.close()


def _load_audit_entries(limit: int = 5000) -> List[dict]:
    bounded = max(1, min(limit, 50000))
    with _db_lock:
        conn = _db_conn()
        try:
            rows = conn.execute(
                "SELECT payload_json FROM audit_entries ORDER BY at DESC LIMIT ?",
                (bounded,),
            ).fetchall()
            return [json.loads(r["payload_json"]) for r in rows]
        finally:
            conn.close()


_init_db()


def _require_admin(user: dict) -> None:
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")

async def get_user_by_email(email: str):
    return None

async def get_user_by_id(user_id: str):
    return None

async def create_user(user_data: dict):
    return user_data

async def get_admin_audit_logs(limit: int = 500):
    rows = _load_audit_entries(limit=max(1, min(limit, 5000)))
    if rows:
        return rows
    return sorted(AUDIT_ENTRIES, key=lambda r: r.get("at", ""), reverse=True)[: max(1, min(limit, 5000))]

async def create_audit_entry(audit_data: dict):
    _persist_audit_entry(audit_data)
    AUDIT_ENTRIES.append(audit_data)
    if len(AUDIT_ENTRIES) > _max_audit_entries():
        del AUDIT_ENTRIES[: len(AUDIT_ENTRIES) - _max_audit_entries()]
    return audit_data

# Pydantic models (imported from shared or defined locally)
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import datetime

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

# Audit endpoints
@audit_router.post("/record")
async def record_audit_event(
    audit_data: dict,
    request: Request,
    user: dict = Depends(verify_service_request)
):
    """Record an audit event (service-to-service communication only)"""
    # In a real implementation, this would validate that the calling service
    # is authorized to write audit events
    
    # Add metadata to the audit entry
    audit_entry = {
        "id": generate_id(),
        "actor_id": audit_data.get("actor_id", "unknown"),
        "actor_email": audit_data.get("actor_email", "unknown@unknown.com"),
        "action": audit_data.get("action", "unknown_action"),
        "target_user_id": audit_data.get("target_user_id"),
        "target_email": audit_data.get("target_email"),
        "changes": audit_data.get("changes", {}),
        "at": now_iso(),
        "ip_address": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
    }
    
    # Create audit entry in database
    created_audit = await create_audit_entry(audit_entry)
    
    return {"ok": True, "audit_id": created_audit["id"]}

@audit_router.get("/")
async def get_audit_logs(
    limit: int = 100,
    offset: int = 0,
    user: dict = Depends(verify_user_request)
):
    """Get audit logs (admin only in real implementation)"""
    _require_admin(user)
    
    logs = await get_admin_audit_logs(limit=limit)
    # Apply offset and limit
    paginated_logs = logs[offset:offset+limit] if offset < len(logs) else []
    
    return {
        "audit": paginated_logs,
        "total": len(logs),
        "limit": limit,
        "offset": offset
    }

# Compliance endpoints
@compliance_router.get("/report")
async def get_compliance_report(
    report_type: str = "summary",
    period: str = "30d",
    user: dict = Depends(verify_user_request)
):
    """Generate compliance report"""
    _require_admin(user)
    
    # Parse period
    days = 30  # default
    if period.endswith('d'):
        try:
            days = int(period[:-1])
        except ValueError:
            pass
    
    # Calculate date range
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    logs = await get_admin_audit_logs(limit=50000)
    in_range = []
    for row in logs:
        ts = row.get("at")
        try:
            dt = datetime.fromisoformat(ts)
        except Exception:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if start_date <= dt <= end_date:
            in_range.append(row)

    actions_breakdown = {}
    daily_breakdown = {}
    for row in in_range:
        action = row.get("action") or "unknown"
        actions_breakdown[action] = actions_breakdown.get(action, 0) + 1
        day_key = (row.get("at") or "")[:10]
        if day_key:
            daily_breakdown[day_key] = daily_breakdown.get(day_key, 0) + 1

    report = {
        "report_type": report_type,
        "period": period,
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "summary": {
            "total_events": len(in_range),
            "unique_actors": len(set([r.get("actor_id") for r in in_range if r.get("actor_id")])),
            "actions_breakdown": actions_breakdown,
            "daily_breakdown": [
                {"date": day, "count": count}
                for day, count in sorted(daily_breakdown.items())
            ]
        },
        "details": in_range[:1000] if report_type == "detailed" else []
    }
    
    return report

@compliance_router.get("/export")
async def export_compliance_data(
    format: str = "json",
    user: dict = Depends(verify_user_request)
):
    """Export compliance data in various formats"""
    _require_admin(user)
    
    # Get audit logs
    logs = await get_admin_audit_logs(limit=5000)
    
    if format.lower() == "csv":
        fields = [
            "id", "at", "actor_id", "actor_email", "action", "target_user_id",
            "target_email", "ip_address", "user_agent", "changes"
        ]
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        for r in logs:
            writer.writerow({
                "id": r.get("id"),
                "at": r.get("at"),
                "actor_id": r.get("actor_id"),
                "actor_email": r.get("actor_email"),
                "action": r.get("action"),
                "target_user_id": r.get("target_user_id"),
                "target_email": r.get("target_email"),
                "ip_address": r.get("ip_address"),
                "user_agent": r.get("user_agent"),
                "changes": json.dumps(r.get("changes") or {}),
            })
        csv_data = out.getvalue()
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=compliance_audit_export.csv"},
        )
    elif format.lower() == "json":
        return {"data": logs, "format": "json", "count": len(logs)}
    else:
        raise HTTPException(status_code=400, detail="Unsupported export format")

# Service-to-service audit recording helper functions
async def record_user_action(
    actor_service: str,
    actor_id: str,
    actor_email: str,
    action: str,
    target_user_id: Optional[str] = None,
    target_email: Optional[str] = None,
    changes: Optional[dict] = None
):
    """Helper function for services to record user actions"""
    audit_data = {
        "actor_id": actor_id,
        "actor_email": actor_email,
        "action": action,
        "target_user_id": target_user_id,
        "target_email": target_email,
        "changes": changes or {},
    }
    
    # In a real implementation, this would make an HTTP call to the auditor service
    # For now, we'll simulate it by calling the create function directly
    return await create_audit_entry({
        "id": generate_id(),
        **audit_data,
        "at": now_iso(),
        "ip_address": "service-to-service",
        "user_agent": f"{actor_service}-service",
    })

async def record_system_event(
    actor_service: str,
    action: str,
    details: Optional[dict] = None
):
    """Helper function for services to record system events"""
    audit_data = {
        "actor_id": actor_service,
        "actor_email": f"{actor_service}@system.internal",
        "action": action,
        "changes": details or {},
    }
    
    # In a real implementation, this would make an HTTP call to the auditor service
    # For now, we'll simulate it by calling the create function directly
    return await create_audit_entry({
        "id": generate_id(),
        **audit_data,
        "at": now_iso(),
        "ip_address": "system-internal",
        "user_agent": f"{actor_service}-service",
    })

# Ensure append-only, tamper-evident storage
# In a real implementation, the auditor service would:
# 1. Use write-once storage (no updates/deletes allowed on audit entries)
# 2. Implement cryptographic hashing/chaining of audit entries
# 3. Store audit logs in append-only format
# 4. Regularly backup and archive audit logs
# 5. Implement access controls to prevent tampering
# 6. Monitor for any attempts to modify or delete audit entries