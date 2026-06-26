"""
API Routes for Payments Service
Contains payment processing, subscription management, and webhook endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, status
from typing import Optional, List
import os
import logging
import json
from datetime import datetime, timedelta

# Import shared components
import sys
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices/shared')

from shared.jwt_utils import create_service_token, verify_service_token, create_user_token, verify_user_token
from shared.security_middleware import verify_service_request, verify_user_request, require_service_auth, require_user_auth
from shared.database_models import *
from shared.utils import now_iso, hash_password, verify_password, SUPPORTED_COUNTRIES, PLANS, CRYPTO_WALLET, PAYMENTS_EMAIL, verify_usdc_tx

# Import local models (would be defined in a models.py file)
# For now, we'll define them inline or import from shared

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("payments.routes")

# Create routers
payment_router = APIRouter()
subscription_router = APIRouter()
webhook_router = APIRouter()

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

async def get_payment_by_id(payment_id: str):
    """Mock function to get payment by ID"""
    # This would be replaced with actual database query
    return None

async def get_payments_by_user_id(user_id: str):
    """Mock function to get payments by user ID"""
    # This would be replaced with actual database query
    return []

async def create_payment(payment_data: dict):
    """Mock function to create a payment"""
    # This would be replaced with actual database insert
    return payment_data

async def update_payment(payment_id: str, update_data: dict):
    """Mock function to update a payment"""
    # This would be replaced with actual database update
    return {**update_data, "id": payment_id}

async def get_user_plan(user_id: str):
    """Mock function to get user's current plan"""
    # This would be replaced with actual database query
    return None

async def update_user_subscription(user_id: str, plan_id: str, status: str):
    """Mock function to update user's subscription"""
    # This would be replaced with actual database update
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
        verification = await verify_usdc_tx(payload.network, payload.tx_hash, plan["price_usd"])
        payment_data["network"] = payload.network
        payment_data["tx_hash"] = payload.tx_hash
        
        if verification:
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
                ADMIN_EMAIL,
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
        if not os.environ.get("STRIPE_SECRET_KEY"):
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
    # In a real implementation, this would verify the webhook signature
    # and process the payment event
    try:
        payload = await request.json()
        logger.info(f"Received Stripe webhook: {json.dumps(payload)}")
        
        # Process the webhook based on event type
        event_type = payload.get("type")
        data = payload.get("data", {}).get("object", {})
        
        if event_type == "payment_intent.succeeded":
            # Payment was completed successfully
            # Update payment status and user subscription
            payment_intent_id = data.get("id")
            # In a real implementation, we would:
            # 1. Find the payment record by stripe_payment_intent_id
            # 2. Update the payment status to "confirmed"
            # 3. Update the user's subscription to "active"
            pass
        elif event_type == "payment_intent.payment_failed":
            # Payment failed
            # Update payment status
            payment_intent_id = data.get("id")
            # In a real implementation, we would:
            # 1. Find the payment record by stripe_payment_intent_id
            # 2. Update the payment status to "failed"
            pass
            
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
    """Mock email service for development"""
    # In production, this would be replaced with real email sending
    print(f"[EMAIL-MOCK] to={to} subject={subject!r}")
    return True

# Pydantic models (imported from shared or defined locally)
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import datetime

class SubscribeIn(BaseModel):
    plan_id: Literal["basic", "pro", "enterprise"]
    payment_method: Literal["interac", "stripe", "crypto"]
    network: Optional[Literal["ethereum", "polygon", "base"]] = None
    tx_hash: Optional[str] = None
    stripe_payment_intent_id: Optional[str] = None
    stripe_client_secret: Optional[str] = None
    note: Optional[str] = None

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