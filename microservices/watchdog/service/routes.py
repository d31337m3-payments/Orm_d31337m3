"""
API Routes for Watchdog Service
Contains service health monitoring, metrics collection, and alerting endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from typing import Optional, List, Dict, Any
import os
import logging
import asyncio
import time
import sqlite3
import json
import threading
import urllib.request
import urllib.error
from datetime import datetime, timedelta

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
logger = logging.getLogger("watchdog.routes")

# Create routers
health_router = APIRouter()
metrics_router = APIRouter()
alert_router = APIRouter()

SERVICE_HEALTH_RECORDS: List[dict] = []
ALERT_RECORDS: List[dict] = []
MAX_HEALTH_RECORDS = int(os.environ.get("WATCHDOG_MAX_HEALTH_RECORDS", "200000"))
MAX_ALERT_RECORDS = int(os.environ.get("WATCHDOG_MAX_ALERT_RECORDS", "200000"))
_db_lock = threading.Lock()

DEFAULT_SERVICE_URLS = {
    "client_index": "http://127.0.0.1:8002",
    "payments": "http://127.0.0.1:8003",
    "data_handling": "http://127.0.0.1:8004",
    "auditor": "http://127.0.0.1:8005",
    "orchestrator": "http://127.0.0.1:8006",
    "watchdog": "http://127.0.0.1:8007",
}


def _service_urls() -> Dict[str, str]:
    raw = get_secret("WATCHDOG_SERVICE_URLS", "") or ""
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return {str(k): str(v).rstrip("/") for k, v in parsed.items() if v}
        except Exception:
            logger.warning("Invalid WATCHDOG_SERVICE_URLS JSON; using defaults")
    return dict(DEFAULT_SERVICE_URLS)


def _health_probe_timeout_seconds() -> int:
    return int(get_secret("WATCHDOG_HEALTH_TIMEOUT_SECONDS", "3") or "3")


def _health_window_minutes() -> int:
    return int(get_secret("WATCHDOG_HEALTH_WINDOW_MINUTES", "60") or "60")


def _db_path() -> str:
    return get_secret("WATCHDOG_DB_PATH", os.environ.get("WATCHDOG_DB_PATH", "/tmp/d31337m3_watchdog.db")) or "/tmp/d31337m3_watchdog.db"


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
                CREATE TABLE IF NOT EXISTS service_health_records (
                    id TEXT PRIMARY KEY,
                    service_name TEXT,
                    status TEXT,
                    timestamp TEXT,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_health_timestamp ON service_health_records(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_health_service ON service_health_records(service_name)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alert_records (
                    id TEXT PRIMARY KEY,
                    service_name TEXT,
                    alert_type TEXT,
                    severity TEXT,
                    created_at TEXT,
                    resolved INTEGER NOT NULL DEFAULT 0,
                    resolved_at TEXT,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_alert_created ON alert_records(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_alert_resolved ON alert_records(resolved)")
            conn.commit()
        finally:
            conn.close()


def _persist_health_record(health_data: dict) -> None:
    with _db_lock:
        conn = _db_conn()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO service_health_records
                (id, service_name, status, timestamp, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    health_data.get("id"),
                    health_data.get("service_name"),
                    health_data.get("status"),
                    health_data.get("timestamp"),
                    json.dumps(health_data),
                ),
            )
            conn.execute(
                """
                DELETE FROM service_health_records
                WHERE id IN (
                    SELECT id FROM service_health_records
                    ORDER BY timestamp DESC
                    LIMIT -1 OFFSET ?
                )
                """,
                (MAX_HEALTH_RECORDS,),
            )
            conn.commit()
        finally:
            conn.close()


def _persist_alert_record(alert_data: dict) -> None:
    with _db_lock:
        conn = _db_conn()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO alert_records
                (id, service_name, alert_type, severity, created_at, resolved, resolved_at, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    alert_data.get("id"),
                    alert_data.get("service_name"),
                    alert_data.get("alert_type"),
                    alert_data.get("severity"),
                    alert_data.get("created_at"),
                    1 if alert_data.get("resolved") else 0,
                    alert_data.get("resolved_at"),
                    json.dumps(alert_data),
                ),
            )
            conn.execute(
                """
                DELETE FROM alert_records
                WHERE id IN (
                    SELECT id FROM alert_records
                    ORDER BY created_at DESC
                    LIMIT -1 OFFSET ?
                )
                """,
                (MAX_ALERT_RECORDS,),
            )
            conn.commit()
        finally:
            conn.close()


_init_db()

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

async def get_service_health_records(limit: int = 100):
    bounded = max(1, min(limit, 5000))
    with _db_lock:
        conn = _db_conn()
        try:
            rows = conn.execute(
                "SELECT payload_json FROM service_health_records ORDER BY timestamp DESC LIMIT ?",
                (bounded,),
            ).fetchall()
            if rows:
                return [json.loads(r["payload_json"]) for r in rows]
        finally:
            conn.close()
    return sorted(SERVICE_HEALTH_RECORDS, key=lambda r: r.get("timestamp", ""), reverse=True)[:bounded]

async def create_service_health_record(health_data: dict):
    health_data.setdefault("id", generate_id())
    _persist_health_record(health_data)
    SERVICE_HEALTH_RECORDS.append(health_data)
    if len(SERVICE_HEALTH_RECORDS) > MAX_HEALTH_RECORDS:
        del SERVICE_HEALTH_RECORDS[: len(SERVICE_HEALTH_RECORDS) - MAX_HEALTH_RECORDS]
    return health_data

async def get_alert_records(limit: int = 100):
    bounded = max(1, min(limit, 5000))
    with _db_lock:
        conn = _db_conn()
        try:
            rows = conn.execute(
                "SELECT payload_json FROM alert_records ORDER BY created_at DESC LIMIT ?",
                (bounded,),
            ).fetchall()
            if rows:
                return [json.loads(r["payload_json"]) for r in rows]
        finally:
            conn.close()
    return sorted(ALERT_RECORDS, key=lambda r: r.get("created_at", ""), reverse=True)[:bounded]

async def create_alert(alert_data: dict):
    _persist_alert_record(alert_data)
    ALERT_RECORDS.append(alert_data)
    if len(ALERT_RECORDS) > MAX_ALERT_RECORDS:
        del ALERT_RECORDS[: len(ALERT_RECORDS) - MAX_ALERT_RECORDS]
    return alert_data

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

# Health check endpoints
@health_router.get("/")
async def get_service_health(
    user: dict = Depends(verify_user_request)
):
    """Get overall system health status"""
    service_urls = _service_urls()
    checks = []
    healthy = 0
    for service_name, service_url in service_urls.items():
        check = await check_service_health(service_name, service_url)
        await record_service_health(check)
        checks.append({
            "name": service_name,
            "status": "ok" if check.get("status") == "healthy" else "degraded",
            "detail": check.get("detail") or "health probe complete",
            "response_time_ms": check.get("response_time_ms"),
        })
        if check.get("status") == "healthy":
            healthy += 1

    overall = "healthy" if healthy == len(service_urls) else ("degraded" if healthy > 0 else "unhealthy")
    health = {
        "service": "watchdog",
        "status": overall,
        "timestamp": now_iso(),
        "checks": checks,
        "ok": overall != "unhealthy"
    }

    return health

@health_router.get("/services")
async def get_services_health(
    user: dict = Depends(verify_user_request)
):
    """Get health status of all registered services"""
    services = []
    for service_name, service_url in _service_urls().items():
        probe = await check_service_health(service_name, service_url)
        await record_service_health(probe)
        services.append({
            "service_name": service_name,
            "status": probe.get("status", "unknown"),
            "last_checked": probe.get("timestamp") or now_iso(),
            "response_time_ms": probe.get("response_time_ms"),
            "details": probe.get("details") or {},
        })

    return {
        "services": services,
        "total": len(services),
        "healthy": len([s for s in services if s["status"] == "healthy"]),
        "timestamp": now_iso()
    }

@health_router.get("/{service_name}")
async def get_service_health_detail(
    service_name: str,
    user: dict = Depends(verify_user_request)
):
    """Get detailed health status for a specific service"""
    service_urls = _service_urls()
    if service_name not in service_urls:
        raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
    probe = await check_service_health(service_name, service_urls[service_name])
    await record_service_health(probe)
    history = await get_service_health_records(limit=500)
    service_history = [r for r in history if r.get("service_name") == service_name]
    avg_response = round(
        sum(float(r.get("response_time_ms", 0) or 0) for r in service_history) / max(1, len(service_history)),
        2,
    )
    error_rate = 0.0
    if service_history:
        unhealthy = len([r for r in service_history if r.get("status") != "healthy"])
        error_rate = round((unhealthy / len(service_history)) * 100, 2)

    health_detail = {
        "service_name": service_name,
        "status": probe.get("status", "unknown"),
        "last_checked": probe.get("timestamp") or now_iso(),
        "response_time_ms": probe.get("response_time_ms"),
        "uptime": probe.get("details", {}).get("uptime", "unknown"),
        "version": probe.get("details", {}).get("version", "unknown"),
        "checks": [
            {
                "name": "API Endpoint",
                "status": "ok" if probe.get("status") == "healthy" else "degraded",
                "detail": probe.get("detail") or "health probe complete",
            }
        ],
        "metrics": {
            "requests_per_minute": probe.get("details", {}).get("requests_per_minute", 0),
            "average_response_time_ms": avg_response,
            "error_rate_percent": error_rate,
        },
    }

    return health_detail

# Metrics endpoints
@metrics_router.get("/")
async def get_system_metrics(
    user: dict = Depends(verify_user_request)
):
    """Get system-wide metrics"""
    records = await get_service_health_records(limit=5000)
    latest_by_service: Dict[str, dict] = {}
    for rec in records:
        svc = rec.get("service_name")
        if svc and svc not in latest_by_service:
            latest_by_service[svc] = rec

    total = len(latest_by_service)
    healthy = len([r for r in latest_by_service.values() if r.get("status") == "healthy"])
    degraded = len([r for r in latest_by_service.values() if r.get("status") == "degraded"])
    unhealthy = max(0, total - healthy - degraded)

    avg_response = round(
        sum(float(r.get("response_time_ms", 0) or 0) for r in latest_by_service.values()) / max(1, total),
        2,
    )

    alerts = await get_alert_records(limit=5000)
    unresolved = len([a for a in alerts if not a.get("resolved")])
    metrics = {
        "timestamp": now_iso(),
        "system": {
            "cpu_usage_percent": None,
            "memory_usage_percent": None,
            "disk_usage_percent": None,
            "load_average": None
        },
        "services": {
            "total_registered": total,
            "healthy": healthy,
            "degraded": degraded,
            "unhealthy": unhealthy
        },
        "traffic": {
            "requests_per_minute": 0,
            "bandwidth_mbps": 0,
            "error_rate_percent": round((unhealthy / max(1, total)) * 100, 2)
        },
        "business": {
            "active_users": None,
            "new_signups_today": None,
            "payments_processed_today": None,
            "scans_completed_today": None
        },
        "watchdog": {
            "average_service_response_time_ms": avg_response,
            "unresolved_alerts": unresolved,
        }
    }

    return metrics

@metrics_router.get("/services/{service_name}")
async def get_service_metrics(
    service_name: str,
    user: dict = Depends(verify_user_request)
):
    """Get metrics for a specific service"""
    service_urls = _service_urls()
    if service_name not in service_urls:
        raise HTTPException(status_code=404, detail=f"Service {service_name} not found")

    records = await get_service_health_records(limit=5000)
    service_records = [r for r in records if r.get("service_name") == service_name]
    if not service_records:
        probe = await check_service_health(service_name, service_urls[service_name])
        await record_service_health(probe)
        service_records = [probe]

    avg_response = round(
        sum(float(r.get("response_time_ms", 0) or 0) for r in service_records) / max(1, len(service_records)),
        2,
    )
    error_count = len([r for r in service_records if r.get("status") != "healthy"])
    error_rate = round((error_count / max(1, len(service_records))) * 100, 2)
    latest = service_records[0]

    metrics = {
        "service_name": service_name,
        "timestamp": now_iso(),
        "performance": {
            "requests_per_minute": latest.get("details", {}).get("requests_per_minute", 0),
            "average_response_time_ms": avg_response,
            "error_rate_percent": error_rate,
            "uptime_percent": round(100 - error_rate, 2)
        },
        "resources": {
            "cpu_usage_percent": latest.get("details", {}).get("cpu_usage_percent"),
            "memory_usage_mb": latest.get("details", {}).get("memory_usage_mb"),
            "disk_usage_mb": latest.get("details", {}).get("disk_usage_mb")
        },
        "business": {
            "daily_operations": len(service_records),
            "success_rate_percent": round(100 - error_rate, 2)
        }
    }

    return metrics

# Alerting endpoints
@alert_router.get("/")
async def get_alerts(
    limit: int = 50,
    offset: int = 0,
    resolved: Optional[bool] = None,
    user: dict = Depends(verify_user_request)
):
    """Get alerts with filtering"""
    # In a real implementation, this would:
    # 1. Retrieve alerts from storage with filtering
    # 2. Apply pagination
    # 3. Return alert details
    
    all_alerts = await get_alert_records(limit=max(1, min(limit + offset + 200, 5000)))
    
    # Apply filters
    filtered_alerts = all_alerts
    if resolved is not None:
        filtered_alerts = [a for a in filtered_alerts if a["resolved"] == resolved]
    
    # Apply pagination
    paginated_alerts = filtered_alerts[offset:offset+limit] if offset < len(filtered_alerts) else []
    
    return {
        "alerts": paginated_alerts,
        "total": len(filtered_alerts),
        "limit": limit,
        "offset": offset,
        "unresolved_count": len([a for a in all_alerts if not a["resolved"]])
    }

@alert_router.post("/")
async def create_alert_endpoint(
    alert_data: dict,
    user: dict = Depends(verify_user_request)
):
    """Create a new alert"""
    alert = {
        "id": generate_id(),
        "service_name": alert_data.get("service_name", "unknown"),
        "alert_type": alert_data.get("alert_type", "general"),
        "severity": alert_data.get("severity", "info"),
        "message": alert_data.get("message", "Alert triggered"),
        "details": alert_data.get("details", {}),
        "created_at": now_iso(),
        "resolved": False,
        "resolved_at": None
    }

    created_alert = await create_alert(alert)
    await send_alert_notification(created_alert)

    return {"ok": True, "alert_id": created_alert["id"]}

@alert_router.patch("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    user: dict = Depends(verify_user_request)
):
    """Mark an alert as resolved"""
    # In a real implementation, this would:
    # 1. Find the alert by ID
    # 2. Update its status to resolved
    # 3. Set resolved timestamp
    # 4. Return success
    
    target = None
    with _db_lock:
        conn = _db_conn()
        try:
            row = conn.execute("SELECT payload_json FROM alert_records WHERE id = ?", (alert_id,)).fetchone()
            if row:
                target = json.loads(row["payload_json"])
        finally:
            conn.close()

    if not target:
        for alert in ALERT_RECORDS:
            if alert.get("id") == alert_id:
                target = alert
                break

    if not target:
        raise HTTPException(status_code=404, detail="Alert not found")

    target["resolved"] = True
    target["resolved_at"] = now_iso()
    _persist_alert_record(target)
    return {"ok": True, "message": f"Alert {alert_id} marked as resolved"}

# Service-to-service health checking helper functions
async def check_service_health(service_name: str, service_url: str) -> dict:
    """Helper function to check the health of a specific service"""
    url = f"{service_url.rstrip('/')}/health"
    started = time.perf_counter()
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=_health_probe_timeout_seconds()) as resp:
            body = resp.read().decode("utf-8")
            elapsed = round((time.perf_counter() - started) * 1000, 2)
            details = {}
            try:
                details = json.loads(body)
            except Exception:
                details = {"raw": body[:500]}
            return {
                "id": generate_id(),
                "service_name": service_name,
                "status": "healthy" if 200 <= resp.status < 300 else "degraded",
                "response_time_ms": elapsed,
                "timestamp": now_iso(),
                "detail": f"HTTP {resp.status}",
                "details": details,
            }
    except urllib.error.HTTPError as e:
        elapsed = round((time.perf_counter() - started) * 1000, 2)
        return {
            "id": generate_id(),
            "service_name": service_name,
            "status": "unhealthy",
            "response_time_ms": elapsed,
            "timestamp": now_iso(),
            "detail": f"HTTP {e.code}",
            "details": {"error": str(e)},
        }
    except Exception as e:
        elapsed = round((time.perf_counter() - started) * 1000, 2)
        return {
            "id": generate_id(),
            "service_name": service_name,
            "status": "unhealthy",
            "response_time_ms": elapsed,
            "timestamp": now_iso(),
            "detail": "probe failed",
            "details": {"error": str(e)},
        }

async def record_service_health(service_health_data: dict):
    """Helper function to record service health data"""
    record = await create_service_health_record(service_health_data)
    await evaluate_alert_conditions()
    return record

# Alerting and notification system
async def send_alert_notification(alert_data: dict):
    """Send alert notifications via configured channels"""
    destination = get_secret("WATCHDOG_ALERT_DESTINATION", "") or ""
    if destination:
        logger.warning("Alert notification [%s] -> %s", destination, alert_data.get("message"))
    else:
        logger.warning("Alert notification: %s", alert_data.get("message"))

async def evaluate_alert_conditions():
    """Evaluate conditions that should trigger alerts"""
    window_start = datetime.now(timezone.utc) - timedelta(minutes=_health_window_minutes())
    records = await get_service_health_records(limit=5000)
    recent = []
    for row in records:
        ts = row.get("timestamp")
        try:
            dt = datetime.fromisoformat(ts)
        except Exception:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt >= window_start:
            recent.append(row)

    if not recent:
        return

    latest_by_service: Dict[str, dict] = {}
    for row in recent:
        svc = row.get("service_name")
        if svc and svc not in latest_by_service:
            latest_by_service[svc] = row

    existing_alerts = await get_alert_records(limit=5000)
    unresolved_services = {
        a.get("service_name")
        for a in existing_alerts
        if not a.get("resolved") and a.get("alert_type") == "service_health"
    }

    for service_name, row in latest_by_service.items():
        if row.get("status") == "healthy":
            continue
        if service_name in unresolved_services:
            continue
        severity = "critical" if row.get("status") == "unhealthy" else "warning"
        alert = {
            "id": generate_id(),
            "service_name": service_name,
            "alert_type": "service_health",
            "severity": severity,
            "message": f"Service {service_name} is {row.get('status')}",
            "details": {
                "response_time_ms": row.get("response_time_ms"),
                "detail": row.get("detail"),
            },
            "created_at": now_iso(),
            "resolved": False,
            "resolved_at": None,
        }
        await create_alert(alert)
        await send_alert_notification(alert)