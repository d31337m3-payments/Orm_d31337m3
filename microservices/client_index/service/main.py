"""
Client Index Service - Main Application Entry Point
Handles user authentication, registration, and profile management
"""

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import shared components
import sys
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices/shared')

from shared.jwt_utils import create_service_token, verify_service_token, create_user_token, verify_user_token
from shared.security_middleware import verify_service_request, verify_user_request, require_service_auth, require_user_auth
from shared.database_models import *
from shared.database import SessionLocal
from shared.repositories import UserRepository, UserSecurityRepository
from shared.utils import now_iso, hash_password, verify_password, SUPPORTED_COUNTRIES, LEGAL_TEMPLATES, _fill_template
from shared.secrets_manager import init_infisical, get_secret

# Initialize Infisical before importing routes to ensure module-level config can read loaded secrets.
init_infisical()

# Import local routers
from .routes import auth_router, user_router, profile_router

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("client_index")

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "https://d31337m3.com,https://www.d31337m3.com,http://localhost:3000,http://127.0.0.1:3000").split(",")
    if o.strip()
]

# Create FastAPI app
app = FastAPI(
    title="Client Index Service",
    description="User authentication and profile management service",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["authentication"])
app.include_router(user_router, prefix="/api/users", tags=["users"])
app.include_router(profile_router, prefix="/api/profile", tags=["profile"])

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"service": "client_index", "status": "healthy", "timestamp": now_iso()}

# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "client_index",
        "version": "1.0.0",
        "description": "User authentication and profile management service",
        "endpoints": {
            "health": "/health",
            "auth": "/api/auth",
            "users": "/api/users",
            "profile": "/api/profile"
        }
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Client Index Service starting up...")
    init_infisical()

    # Bootstrap an admin account from secrets when it does not yet exist.
    admin_email = (get_secret("ADMIN_EMAIL", os.environ.get("ADMIN_EMAIL", "")) or "").strip().lower()
    admin_password = (get_secret("ADMIN_PASSWORD", os.environ.get("ADMIN_PASSWORD", "")) or "").strip()
    if admin_email and admin_password:
        db = SessionLocal()
        try:
            existing = UserRepository.get_by_email(db, admin_email)
            if not existing:
                UserRepository.create(
                    db,
                    {
                        "email": admin_email,
                        "name": "Admin",
                        "password_hash": hash_password(admin_password),
                        "auth_provider": "password",
                        "is_admin": True,
                        "is_active": True,
                        "plan_id": None,
                        "subscription_status": "active",
                        "subscription_started_at": None,
                    },
                )
                logger.info("Bootstrapped admin user from secrets")
            elif not existing.is_admin:
                UserRepository.update(db, existing.id, {"is_admin": True})
                logger.info("Upgraded existing user to admin based on ADMIN_EMAIL")
        except Exception as e:
            logger.warning(f"Admin bootstrap warning: {e}")
        finally:
            db.close()

    # Migration-safe defaults: ensure security rows exist for all users.
    db = SessionLocal()
    try:
        users = UserRepository.list_all(db, skip=0, limit=100000)
        created = 0
        for u in users:
            sec = UserSecurityRepository.get_by_user_id(db, u.id)
            if not sec:
                UserSecurityRepository.ensure(db, u.id, email_verified=True)
                created += 1
        if created:
            logger.info(f"Backfilled user_security rows: {created}")
    except Exception as e:
        logger.warning(f"user_security backfill warning: {e}")
    finally:
        db.close()

    logger.info("Client Index Service started successfully")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Client Index Service shutting down...")
    # In a real implementation, you would close database connections here
    logger.info("Client Index Service shut down successfully")