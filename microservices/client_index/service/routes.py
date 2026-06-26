"""
API Routes for Client Index Service
Contains authentication, user management, and profile endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundRequests, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import os
import logging

# Import shared components
import sys
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices/shared')

from shared.jwt_utils import create_service_token, verify_service_token, create_user_token, verify_user_token
from shared.security_middleware import verify_service_request, verify_user_request, require_service_auth, require_user_auth
from shared.database_models import *
from shared.utils import now_iso, hash_password, verify_password, SUPPORTED_COUNTRIES, DATA_BROKERS, LEGAL_TEMPLATES, _fill_template, find_promo_for_code, promo_is_expired, build_promo_code

# Import database (would be initialized in main.py in a real implementation)
# For now, we'll simulate with in-memory storage or mock database calls

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("client_index.routes")

# Create routers
auth_router = APIRouter()
user_router = APIRouter()
profile_router = APIRouter()

# Security schemes
bearer = HTTPBearer(auto_error=False)

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

async def update_user(user_id: str, update_data: dict):
    """Mock function to update a user"""
    # This would be replaced with actual database update
    return {**update_data, "id": user_id}

async def get_profile_by_user_id(user_id: str):
    """Mock function to get profile by user ID"""
    # This would be replaced with actual database query
    return None

async def create_profile(profile_data: dict):
    """Mock function to create a profile"""
    # This would be replaced with actual database insert
    return profile_data

async def update_profile(user_id: str, update_data: dict):
    """Mock function to update a profile"""
    # This would be replaced with actual database update
    return {**update_data, "user_id": user_id}

# Authentication endpoints
@auth_router.post("/register")
async def register(payload: UserCreate, background: BackgroundTasks, request: Request):
    """Register a new user"""
    ip = request.client.host if request.client else "anon"
    
    # Rate limiting
    allowed, retry = _ratelimit(f"register:{ip}")
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Too many signups from this IP. Try again in {retry // 60}m.")
    
    # Check if user already exists
    existing_user = await get_user_by_email(payload.email.lower())
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Validate promo code if provided
    promo = None
    if payload.promo_code and payload.promo_code.strip():
        promo = find_promo_for_code(payload.promo_code, [])  # Would get from DB/config
        if not promo:
            raise HTTPException(status_code=400, detail="Invalid promo code")
        if promo_is_expired(promo):
            raise HTTPException(status_code=400, detail="Promo code expired")
    
    # Create user
    user_data = {
        "id": generate_id(),
        "email": payload.email.lower(),
        "name": payload.name or payload.email.split("@")[0],
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
        user_data["promo_code"] = promo["code"]
        user_data["promo_discount_percent"] = promo["percent_off"]
        user_data["promo_expires_at"] = promo["expires_raw"]
    
    # Create user in database
    created_user = await create_user(user_data)
    
    # Create initial profile
    profile_data = {
        "user_id": created_user["id"],
        "name": created_user["name"],
        "address": "",
        "phone": "",
        "country": "CA",  # Default to Canada
        "state": "ON",
        "updated_at": now_iso(),
    }
    await create_profile(profile_data)
    
    # Add initial keyword (user's name)
    if created_user["name"] and len(created_user["name"]) >= 3 and "@" not in created_user["name"]:
        keyword_data = {
            "id": generate_id(),
            "user_id": created_user["id"],
            "value": created_user["name"],
            "type": "name",
            "created_at": now_iso(),
            "last_scan_at": None,
        }
        # Would save to database in real implementation
        
        # Trigger initial scan (background task)
        # background.add_task(scan_and_notify, created_user["id"], payload.email, [keyword_data["id"]])
    
    # Send welcome email
    # background.add_task(
    #     send_email_mock,
    #     payload.email,
    #     "Welcome to d31337m3 — Made in Canada",
    #     f"Hi {created_user['name']},\n\nYour account is ready. We're already running your first scan across Google, Bing, and 15+ data brokers — check your dashboard in a couple of minutes.\n\nMade with pride in Canada.\n\n— d31337m3"
    # )
    
    # Create access token
    token = create_user_token(created_user["id"], False, "client_index")
    
    # Return response
    response_user = {
        "id": created_user["id"],
        "email": created_user["email"],
        "name": created_user["name"],
        "is_admin": False,
        "plan_id": None,
        "subscription_status": "trial"
    }
    
    if promo:
        response_user["promo_code"] = promo["code"]
        response_user["promo_discount_percent"] = promo["percent_off"]
        response_user["promo_expires_at"] = promo["expires_raw"]
    
    return {"token": token, "user": response_user}

@auth_router.post("/login")
async def login(payload: UserLogin, request: Request):
    """Login an existing user"""
    ip = (request.client.host if request.client else "anon") + ":" + payload.email.lower()
    
    # Rate limiting
    allowed, retry = _ratelimit(f"login:{ip}")
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Too many attempts. Try again in {retry // 60}m {retry % 60}s.")
    
    # Get user by email
    user = await get_user_by_email(payload.email.lower())
    if not user or not user.get("password_hash") or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create access token
    token = create_user_token(user["id"], user.get("is_admin", False), "client_index")
    
    # Return response
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user.get("name"),
            "is_admin": user.get("is_admin", False),
            "plan_id": user.get("plan_id"),
            "subscription_status": user.get("subscription_status", "trial"),
        }
    }

@auth_router.get("/me")
async def get_current_user_info(user: dict = Depends(verify_user_request)):
    """Get current user information"""
    # In a real implementation, this would fetch fresh data from the database
    return {"user": user}

# User management endpoints
@user_router.get("/")
async def get_users(skip: int = 0, limit: int = 100, user: dict = Depends(require_service_auth("orchestrator"))):
    """Get list of users (for orchestrator/service-to-service communication)"""
    # In a real implementation, this would query the database with pagination
    return {"users": [], "count": 0}

@user_router.get("/{user_id}")
async def get_user(user_id: str, user: dict = Depends(require_service_auth())):
    """Get a specific user by ID"""
    # In a real implementation, this would fetch from database
    user_data = await get_user_by_id(user_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": user_data}

# Profile endpoints
@profile_router.get("/")
async def get_profile(user: dict = Depends(verify_user_request)):
    """Get current user's profile"""
    profile_data = await get_profile_by_user_id(user["id"])
    if not profile_data:
        # Return default profile if none exists
        return {
            "profile": {
                "user_id": user["id"],
                "name": user.get("name", ""),
                "address": "",
                "phone": "",
                "country": "CA",
                "state": "ON",
                "updated_at": now_iso(),
            }
        }
    return {"profile": profile_data}

@profile_router.put("/")
async def update_profile_endpoint(payload: ProfileCreate, user: dict = Depends(verify_user_request)):
    """Update current user's profile"""
    # Ensure user can only update their own profile
    if payload.user_id != user["id"]:
        raise HTTPException(status_code=403, detail="Can only update own profile")
    
    # Update user name if provided
    if payload.name:
        await update_user(user["id"], {"name": payload.name})
    
    # Update profile
    update_data = {
        "name": payload.name,
        "address": payload.address,
        "phone": payload.phone,
        "country": payload.country,
        "state": payload.state,
        "updated_at": now_iso(),
    }
    
    # Remove None values
    update_data = {k: v for k, v in update_data.items() if v is not None}
    
    updated_profile = await update_profile(user["id"], update_data)
    return {"profile": updated_profile}