"""
Payments Service - Main Application Entry Point
Handles payment processing, subscription management, and billing
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
from shared.utils import now_iso, hash_password, verify_password, SUPPORTED_COUNTRIES, PLANS, CRYPTO_WALLET, PAYMENTS_EMAIL

# Import local routers
from .routes import payment_router, subscription_router, webhook_router

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("payments")

# Create FastAPI app
app = FastAPI(
    title="Payments Service",
    description="Payment processing and subscription management service",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(payment_router, prefix="/api/payments", tags=["payments"])
app.include_router(subscription_router, prefix="/api/subscriptions", tags=["subscriptions"])
app.include_router(webhook_router, prefix="/api/webhooks", tags=["webhooks"])

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"service": "payments", "status": "healthy", "timestamp": now_iso()}

# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "payments",
        "version": "1.0.0",
        "description": "Payment processing and subscription management service",
        "endpoints": {
            "health": "/health",
            "payments": "/api/payments",
            "subscriptions": "/api/subscriptions",
            "webhooks": "/api/webhooks"
        }
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Payments Service starting up...")
    logger.info("Payments Service started successfully")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Payments Service shutting down...")
    logger.info("Payments Service shut down successfully")