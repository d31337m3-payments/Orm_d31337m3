from __future__ import annotations

"""
API Routes for Payments Service
Contains payment processing, subscription management, and webhook endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, status
from typing import Optional, List, Dict, Literal
import logging
import json
import sqlite3
import threading
import re
import hmac
import hashlib
import time
from datetime import datetime, timedelta
from pydantic import BaseModel

# Import shared components
import sys
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices/shared')

from shared.jwt_utils import create_service_token, verify_service_token, create_user_token, verify_user_token
from shared.security_middleware import verify_service_request, verify_user_request, require_service_auth, require_user_auth
from shared.database_models import *
from shared.utils import now_iso, hash_password, verify_password, SUPPORTED_COUNTRIES, PLANS, CRYPTO_WALLET, PAYMENTS_EMAIL, verify_usdc_tx
from shared.secrets_manager import get_secret, get_int_secret, get_bool_secret

# Import local models (would be defined in a models.py file)
# For now, we'll define them inline or import from shared

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("payments.routes")

TX_HASH_RE = re.compile(r"^0x[a-fA-F0-9]{64}$")

_db_lock = threading.Lock()

# Bounded in-memory stores for launch reliability.
PAYMENT_STORE: Dict[str, dict] = {}
USER_PAYMENTS: Dict[str, List[str]] = {}
USER_SUBSCRIPTIONS: Dict[str, dict] = {}
MAX_PAYMENTS_IN_MEMORY = get_int_secret("PAYMENTS_MAX_RECORDS", 100000)


def _payments_db_path() -> str:
    return get_secret("PAYMENTS_DB_PATH", "/tmp/d31337m3_payments.db") or "/tmp/d31337m3_payments.db"


def _admin_email() -> str:
    return get_secret("ADMIN_EMAIL", "admin@example.com") or "admin@example.com"


def _allow_placeholder_crypto_verification() -> bool:
    return get_bool_secret("ALLOW_PLACEHOLDER_CRYPTO_VERIFICATION", False)


def _stripe_webhook_secret() -> str:
    return get_secret("STRIPE_WEBHOOK_SECRET", "") or ""


def _stripe_webhook_tolerance_seconds() -> int:
    return get_int_secret("STRIPE_WEBHOOK_TOLERANCE_SECONDS", 300)


def _stripe_secret_key() -> str:
    return get_secret("STRIPE_SECRET_KEY", "") or ""


def _db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_payments_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _init_store_db() -> None:
    with _db_lock:
        conn = _db_conn()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS payments (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    plan_id TEXT,
                    amount_usd REAL,
                    method TEXT,
                    status TEXT,
                    stripe_payment_intent_id TEXT,
                    tx_hash TEXT,
                    network TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_intent ON payments(stripe_payment_intent_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_tx ON payments(tx_hash)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS subscriptions (
                    user_id TEXT PRIMARY KEY,
                    plan_id TEXT,
                    status TEXT,
                    started_at TEXT,
                    expires_at TEXT,
                    updated_at TEXT
                )
                """
            )
            conn.commit()
        finally:
            conn.close()


def _persist_payment(payment_data: dict) -> None:
    with _db_lock:
        conn = _db_conn()
        try:
            now = now_iso()
            conn.execute(
                """
                INSERT OR REPLACE INTO payments
                (id, user_id, plan_id, amount_usd, method, status, stripe_payment_intent_id, tx_hash, network, created_at, updated_at, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payment_data["id"],
                    payment_data.get("user_id"),
                    payment_data.get("plan_id"),
                    float(payment_data.get("amount_usd", 0) or 0),
                    payment_data.get("method"),
                    payment_data.get("status"),
                    payment_data.get("stripe_payment_intent_id"),
                    payment_data.get("tx_hash"),
                    payment_data.get("network"),
                    payment_data.get("created_at") or now,
                    now,
                    json.dumps(payment_data),
                ),
            )
            conn.commit()
        finally:
            conn.close()


def _load_payment(payment_id: str) -> Optional[dict]:
    with _db_lock:
        conn = _db_conn()
        try:
            row = conn.execute("SELECT payload_json FROM payments WHERE id = ?", (payment_id,)).fetchone()
            if not row:
                return None
            return json.loads(row["payload_json"])
        finally:
            conn.close()


def _load_user_payments(user_id: str) -> List[dict]:
    with _db_lock:
        conn = _db_conn()
        try:
            rows = conn.execute(
                "SELECT payload_json FROM payments WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, MAX_PAYMENTS_IN_MEMORY),
            ).fetchall()
            return [json.loads(r["payload_json"]) for r in rows]
        finally:
            conn.close()


def _find_payment_by_intent(intent_id: str) -> Optional[dict]:
    if not intent_id:
        return None
    with _db_lock:
        conn = _db_conn()
        try:
            row = conn.execute(
                "SELECT payload_json FROM payments WHERE stripe_payment_intent_id = ? ORDER BY created_at DESC LIMIT 1",
                (intent_id,),
            ).fetchone()
            return json.loads(row["payload_json"]) if row else None
        finally:
            conn.close()


def _find_payment_by_tx_hash(tx_hash: str) -> Optional[dict]:
    if not tx_hash:
        return None
    with _db_lock:
        conn = _db_conn()
        try:
            row = conn.execute(
                "SELECT payload_json FROM payments WHERE tx_hash = ? ORDER BY created_at DESC LIMIT 1",
                (tx_hash,),
            ).fetchone()
            return json.loads(row["payload_json"]) if row else None
        finally:
            conn.close()


def _persist_subscription(user_id: str, plan_id: str, status_value: str) -> None:
    with _db_lock:
        conn = _db_conn()
        try:
            prev = conn.execute("SELECT started_at FROM subscriptions WHERE user_id = ?", (user_id,)).fetchone()
            started_at = prev["started_at"] if prev and prev["started_at"] else now_iso()
            conn.execute(
                """
                INSERT OR REPLACE INTO subscriptions
                (user_id, plan_id, status, started_at, expires_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, plan_id, status_value, started_at, None, now_iso()),
            )
            conn.commit()
        finally:
            conn.close()


def _load_subscription(user_id: str) -> Optional[dict]:
    with _db_lock:
        conn = _db_conn()
        try:
            row = conn.execute("SELECT * FROM subscriptions WHERE user_id = ?", (user_id,)).fetchone()
            if not row:
                return None
            return {
                "user_id": row["user_id"],
                "plan_id": row["plan_id"],
                "status": row["status"],
                "started_at": row["started_at"],
                "expires_at": row["expires_at"],
                "updated_at": row["updated_at"],
            }
        finally:
            conn.close()


def _verify_stripe_signature(raw_body: bytes, stripe_signature: str) -> bool:
    webhook_secret = _stripe_webhook_secret()
    if not webhook_secret:
        return False
    if not stripe_signature:
        return False

    parts = {}
    for p in stripe_signature.split(","):
        if "=" in p:
            k, v = p.split("=", 1)
            parts.setdefault(k, []).append(v)

    ts_values = parts.get("t") or []
    sig_values = parts.get("v1") or []
    if not ts_values or not sig_values:
        return False

    ts = ts_values[0]
    try:
        ts_int = int(ts)
    except ValueError:
        return False

    now_ts = int(time.time())
    if abs(now_ts - ts_int) > _stripe_webhook_tolerance_seconds():
        return False

    signed_payload = f"{ts}.{raw_body.decode('utf-8')}".encode("utf-8")
    expected = hmac.new(webhook_secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    for incoming in sig_values:
        if hmac.compare_digest(expected, incoming):
            return True
    return False


_init_store_db()

# Create routers
payment_router = APIRouter()
subscription_router = APIRouter()
webhook_router = APIRouter()


class SubscribeIn(BaseModel):
    plan_id: Literal["basic", "pro", "enterprise"]
    payment_method: Literal["interac", "stripe", "crypto"]
    network: Optional[Literal["ethereum", "polygon", "base"]] = None
    tx_hash: Optional[str] = None
    stripe_payment_intent_id: Optional[str] = None
    stripe_client_secret: Optional[str] = None
    note: Optional[str] = None

# In-memory persistence helpers (replace no-op mocks).
async def get_user_by_email(email: str):
    return None

async def get_user_by_id(user_id: str):
    return None

async def create_user(user_data: dict):
    return user_data

async def get_payment_by_id(payment_id: str):
    payment = _load_payment(payment_id)
    if payment:
        return payment
    return PAYMENT_STORE.get(payment_id)

async def get_payments_by_user_id(user_id: str):
    rows = _load_user_payments(user_id)
    if rows:
        return rows
    ids = USER_PAYMENTS.get(user_id, [])
    return [PAYMENT_STORE[p] for p in ids if p in PAYMENT_STORE]

async def create_payment(payment_data: dict):
    _persist_payment(payment_data)
    PAYMENT_STORE[payment_data["id"]] = payment_data
    USER_PAYMENTS.setdefault(payment_data["user_id"], []).append(payment_data["id"])
    if len(PAYMENT_STORE) > MAX_PAYMENTS_IN_MEMORY:
        ordered = sorted(PAYMENT_STORE.items(), key=lambda kv: kv[1].get("created_at", ""))
        for old_id, old_payment in ordered[: len(PAYMENT_STORE) - MAX_PAYMENTS_IN_MEMORY]:
            PAYMENT_STORE.pop(old_id, None)
            uid = old_payment.get("user_id")
            if uid in USER_PAYMENTS:
                USER_PAYMENTS[uid] = [x for x in USER_PAYMENTS[uid] if x != old_id]
    return payment_data

async def update_payment(payment_id: str, update_data: dict):
    payment = await get_payment_by_id(payment_id)
    if not payment:
        return None
    payment.update(update_data)
    payment["updated_at"] = now_iso()
    _persist_payment(payment)
    PAYMENT_STORE[payment_id] = payment
    return payment

async def get_user_plan(user_id: str):
    sub = _load_subscription(user_id)
    if sub:
        return sub
    return USER_SUBSCRIPTIONS.get(user_id)

async def update_user_subscription(user_id: str, plan_id: str, status: str):
    _persist_subscription(user_id, plan_id, status)
    USER_SUBSCRIPTIONS[user_id] = {
        "plan_id": plan_id,
        "status": status,
        "started_at": USER_SUBSCRIPTIONS.get(user_id, {}).get("started_at") or now_iso(),
        "expires_at": None,
        "updated_at": now_iso(),
    }
    return True

# Payment endpoints
@payment_router.post("/")
async def process_payment(payload: SubscribeIn, background: BackgroundTasks, request: Request, user: dict = Depends(verify_user_request)):
    """Process a payment for subscription"""
    # Get the plan details
    plan = PLANS[payload.plan_id]
    
    # Create payment record
    payment_data = {
        "id": generate_id(),
        "user_id": user["id"],
        "plan_id": plan["id"],
        "amount_usd": plan["price_usd"],
        "method": payload.payment_method,
        "status": "pending",
        "created_at": now_iso(),
    }
    
    # Handle different payment methods
    if payload.payment_method == "interac":
        payment_data["instructions"] = {
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
                f"5. Admin will confirm within 24 hours and unlock your subscription.\n"
            ),
        }
        payment_data["status"] = "awaiting_confirmation"
        
        # Create payment in database
        created_payment = await create_payment(payment_data)
        
        # Send notification email
        background.add_task(
            send_email_mock,
            PAYMENTS_EMAIL,
            f"[d31337m3] Interac payment expected — {user['email']}",
            f"User {user['email']} initiated {plan['name']} (${plan['price_usd']}) via Interac e-Transfer (auto-deposit).\n"
            f"Payment ID: {created_payment['id']}\n"
            f"Expected note: d31337m3 {plan['name']} - {user['email']}\n\n"
            f"Confirm via admin panel once funds arrive.\n"
        )
        
        return {
            "payment_id": created_payment["id"],
            "status": "awaiting_confirmation",
            "instructions": created_payment["instructions"]
        }

    elif payload.payment_method == "crypto":
        if not payload.network or not payload.tx_hash:
            # Step 1: user requested wallet/instructions
            payment_data["instructions"] = {
                "wallet": CRYPTO_WALLET,
                "networks": ["ethereum", "polygon", "base"],
                "amount_usdc": plan["price_usd"],
                "memo": f"d31337m3-{user['id'][:8]}",
            }
            payment_data["status"] = "awaiting_tx_hash"
            
            # Create payment in database
            created_payment = await create_payment(payment_data)
            
            return {
                "payment_id": created_payment["id"],
                "status": "awaiting_tx_hash",
                "instructions": created_payment["instructions"]
            }

        # Step 2: verify tx hash
        if not TX_HASH_RE.match(payload.tx_hash):
            raise HTTPException(status_code=400, detail="Invalid transaction hash format")

        existing_tx = _find_payment_by_tx_hash(payload.tx_hash)
        if existing_tx and existing_tx.get("user_id") != user["id"]:
            raise HTTPException(status_code=409, detail="Transaction hash already used")

        verification = await verify_usdc_tx(payload.network, payload.tx_hash, plan["price_usd"])
        payment_data["network"] = payload.network
        payment_data["tx_hash"] = payload.tx_hash
        
        if verification and (
            verification.get("verification_mode") != "placeholder"
            or _allow_placeholder_crypto_verification()
        ):
            payment_data["status"] = "confirmed"
            payment_data["verification"] = verification
            
            # Create payment in database
            created_payment = await create_payment(payment_data)
            
            # Update user's subscription
            await update_user_subscription(
                user["id"], 
                plan["id"], 
                "active"
            )
            
            # Send confirmation email
            background.add_task(
                send_email_mock,
                user["email"],
                f"[d31337m3] Payment confirmed — {plan['name']}",
                f"Your USDC payment of ${plan['price_usd']} on {payload.network} has been confirmed.\n"
                f"Tx: {payload.tx_hash}\n\n— d31337m3\n"
            )
            
            return {
                "payment_id": created_payment["id"],
                "status": "confirmed",
                "verification": verification
            }
        else:
            payment_data["status"] = "pending_manual_review"
            
            # Create payment in database
            created_payment = await create_payment(payment_data)
            
            # Send notification for manual review
            background.add_task(
                send_email_mock,
                _admin_email(),
                f"[d31337m3] Crypto payment needs manual review — {user['email']}",
                f"Tx hash {payload.tx_hash} on {payload.network} could not be auto-verified for ${plan['price_usd']}. "
                f"Please review in admin panel.\n"
            )
            
            return {
                "payment_id": created_payment["id"],
                "status": "pending_manual_review",
                "message": "Transaction not auto-verified. Our team will manually review within 24 hours."
            }

    elif payload.payment_method == "stripe":
        if not _stripe_secret_key():
            payment_data["status"] = "stripe_unavailable"
            payment_data["instructions"] = {
                "message": "Stripe credentials not yet configured. Please use Interac or Crypto, or contact support."
            }
            
            # Create payment in database
            created_payment = await create_payment(payment_data)
            
            return {
                "payment_id": created_payment["id"],
                "status": "stripe_unavailable",
                "message": "Stripe is being set up. Please use Interac or Crypto for now."
            }
        
        # In a real implementation, we would create a Stripe PaymentIntent here
        # For now, we'll simulate the Stripe integration
        payment_data["stripe_payment_intent_id"] = f"pi_{generate_id()[:10]}"
        payment_data["stripe_client_secret"] = f"pi_{generate_id()[:10]}_secret_{generate_id()[:10]}"
        payment_data["status"] = "pending_stripe_confirmation"
        
        # Create payment in database
        created_payment = await create_payment(payment_data)
        
        return {
            "payment_id": created_payment["id"],
            "status": "pending_stripe_confirmation",
            "client_secret": created_payment["stripe_client_secret"],
            "payment_intent_id": created_payment["stripe_payment_intent_id"]
        }

    else:
        raise HTTPException(status_code=400, detail="Unsupported payment method")

@payment_router.get("/")
async def list_user_payments(user: dict = Depends(verify_user_request)):
    """List payments for the current user"""
    payments = await get_payments_by_user_id(user["id"])
    return {"payments": payments}

@payment_router.get("/{payment_id}")
async def get_payment(payment_id: str, user: dict = Depends(verify_user_request)):
    """Get a specific payment by ID"""
    payment = await get_payment_by_id(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Ensure user can only access their own payments
    if payment["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {"payment": payment}

# Subscription endpoints
@subscription_router.get("/")
async def get_user_subscription(user: dict = Depends(verify_user_request)):
    """Get current user's subscription"""
    subscription = await get_user_plan(user["id"])
    if not subscription:
        return {
            "subscription": {
                "plan_id": None,
                "plan_name": None,
                "status": "trial",
                "started_at": None,
                "expires_at": None
            }
        }
    
    plan_details = PLANS.get(subscription["plan_id"], {})
    return {
        "subscription": {
            "plan_id": subscription["plan_id"],
            "plan_name": plan_details.get("name"),
            "status": subscription["status"],
            "started_at": subscription.get("started_at"),
            "expires_at": subscription.get("expires_at")
        }
    }

@subscription_router.post("/")
async def update_subscription(payload: SubscribeIn, background: BackgroundTasks, user: dict = Depends(verify_user_request)):
    """Update user's subscription (alias for payment processing)"""
    # This is essentially the same as processing a payment
    return await process_payment(payload, background, request=None, user=user)

# Webhook endpoints for external payment providers
@webhook_router.post("/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks"""
    raw = await request.body()
    signature = request.headers.get("stripe-signature", "")
    if not _verify_stripe_signature(raw, signature):
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    try:
        payload = json.loads(raw.decode("utf-8"))
        logger.info(f"Received Stripe webhook: {json.dumps(payload)}")
        
        # Process the webhook based on event type
        event_type = payload.get("type")
        data = payload.get("data", {}).get("object", {})
        
        if event_type == "payment_intent.succeeded":
            payment_intent_id = data.get("id")
            payment = _find_payment_by_intent(payment_intent_id)
            if payment:
                await update_payment(payment["id"], {
                    "status": "confirmed",
                    "stripe_webhook_confirmed_at": now_iso(),
                    "stripe_event_id": payload.get("id"),
                })
                await update_user_subscription(payment["user_id"], payment["plan_id"], "active")
        elif event_type == "payment_intent.payment_failed":
            payment_intent_id = data.get("id")
            payment = _find_payment_by_intent(payment_intent_id)
            if payment:
                await update_payment(payment["id"], {
                    "status": "failed",
                    "stripe_webhook_failed_at": now_iso(),
                    "stripe_event_id": payload.get("id"),
                })
            
        return {"status": "processed"}
    except Exception as e:
        logger.error(f"Error processing Stripe webhook: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

@webhook_router.post("/interac")
async def interac_webhook(request: Request):
    """Handle Interac webhooks (if applicable)"""
    # In a real implementation, this would verify the webhook signature
    # and process the payment event
    try:
        payload = await request.json()
        logger.info(f"Received Interac webhook: {json.dumps(payload)}")
        
        # Process the webhook
        # Update payment status and user subscription
        
        return {"status": "processed"}
    except Exception as e:
        logger.error(f"Error processing Interac webhook: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

# Email service mock (can be replaced with real implementation)
async def send_email_mock(to: str, subject: str, body: str, attachments: Optional[List[Dict]] = None) -> bool:
    """Development email sink; logs only when SMTP is not wired for this service."""
    logger.info(f"[EMAIL-MOCK] to={to} subject={subject!r}")
    return True

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