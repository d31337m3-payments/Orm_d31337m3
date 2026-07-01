"""
Auditor Service - Main Application Entry Point
Handles audit trail recording, compliance reporting, and tamper-evident logging
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import shared components
import sys
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices/shared')

from shared.jwt_utils import create_service_token, verify_service_token, create_user_token, verify_user_token
from shared.security_middleware import verify_service_request, verify_user_request, require_service_auth, require_user_auth
from shared.database_models import *
from shared.utils import now_iso, hash_password, verify_password, SUPPORTED_COUNTRIES
from shared.secrets_manager import init_infisical, get_cors_allowed_origins

# Initialize Infisical before importing routes to ensure module-level config can read loaded secrets.
init_infisical()

# Import local routers
from .routes import audit_router, compliance_router

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("auditor")

CORS_ALLOWED_ORIGINS = get_cors_allowed_origins()
STARTED_AT = now_iso()

# Create FastAPI app
app = FastAPI(
    title="Auditor Service",
    description="Audit trail recording and compliance reporting service",
    version="1.0.3"
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
app.include_router(audit_router, prefix="/api/audit", tags=["audit"])
app.include_router(compliance_router, prefix="/api/compliance", tags=["compliance"])

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "service": "auditor",
        "status": "healthy",
        "version": app.version,
        "started_at": STARTED_AT,
        "timestamp": now_iso()
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "auditor",
        "version": "1.0.0",
        "description": "Audit trail recording and compliance reporting service",
        "endpoints": {
            "health": "/health",
            "audit": "/api/audit",
            "compliance": "/api/compliance"
        }
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Auditor Service starting up...")
    init_infisical()
    logger.info("Auditor Service started successfully")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Auditor Service shutting down...")
    logger.info("Auditor Service shut down successfully")