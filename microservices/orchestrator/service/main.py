"""
Orchestrator Service - Main Application Entry Point
Manages service discovery, startup ordering, and lifecycle events
"""

import os
import logging
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional

# Import shared components
import sys
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices/shared')

from shared.jwt_utils import create_service_token, verify_service_token, verify_user_token, create_user_token
from shared.security_middleware import verify_service_request, require_service_auth, verify_user_request
from shared.database_models import generate_id, now_iso
from shared.utils import SUPPORTED_COUNTRIES
from shared.secrets_manager import init_infisical

# Initialize Infisical before importing routes to ensure module-level config can read loaded secrets.
init_infisical()

# Import local routers
from .routes import (
    service_router,
    health_router,
    admin_router,
    support_router,
    workforce_router,
    run_support_state_cleanup,
    support_anon_cleanup_interval_seconds,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("orchestrator")

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "https://d31337m3.com,https://www.d31337m3.com,http://localhost:3000,http://127.0.0.1:3000").split(",")
    if o.strip()
]

# Create FastAPI app
app = FastAPI(
    title="Orchestrator Service",
    description="Service discovery and lifecycle management for microservices",
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
app.include_router(service_router, prefix="/api/services", tags=["services"])
app.include_router(health_router, prefix="/api/health", tags=["health"])
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
app.include_router(support_router, prefix="/api/support", tags=["support"])
app.include_router(workforce_router, prefix="/api/workforce", tags=["workforce"])

# Service registry (in production, this would be more sophisticated)
SERVICE_REGISTRY: Dict[str, dict] = {}
SERVICE_STARTUP_ORDER = [
    "auditor",      # 1. Available for event recording
    "client_index", # 2. Identity and auth ready
    "data_handling",# 3. Data store ready
    "payments",     # 4. Billing flows ready
    "watchdog",     # 5. Monitoring can begin
    "orchestrator"  # 6. Coordinates the others and exposes global state
]

_support_cleanup_task: Optional[asyncio.Task] = None


async def _support_cleanup_loop():
    while True:
        try:
            stats = run_support_state_cleanup()
            removed_total = stats.get("removed_challenges", 0) + stats.get("removed_sessions", 0)
            if removed_total:
                logger.info(
                    "Support anon cleanup removed %s challenge(s), %s session(s)",
                    stats.get("removed_challenges", 0),
                    stats.get("removed_sessions", 0),
                )
        except Exception as e:
            logger.warning(f"Support anon cleanup loop warning: {e}")
        await asyncio.sleep(max(30, support_anon_cleanup_interval_seconds()))

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "service": "orchestrator", 
        "status": "healthy", 
        "timestamp": now_iso(),
        "registered_services": len(SERVICE_REGISTRY),
        "services": list(SERVICE_REGISTRY.keys())
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "orchestrator",
        "version": "1.0.0",
        "description": "Service discovery and lifecycle management for microservices",
        "endpoints": {
            "health": "/health",
            "services": "/api/services",
            "health_checks": "/api/health"
        },
        "startup_order": SERVICE_STARTUP_ORDER
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    global _support_cleanup_task
    logger.info("Orchestrator Service starting up...")
    logger.info(f"Service startup order: {SERVICE_STARTUP_ORDER}")
    init_infisical()
    # Start periodic cleanup for ephemeral anonymous support OTP/session stores.
    _support_cleanup_task = asyncio.create_task(_support_cleanup_loop())
    run_support_state_cleanup()
    logger.info("Orchestrator Service started successfully")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    global _support_cleanup_task
    logger.info("Orchestrator Service shutting down...")
    if _support_cleanup_task:
        _support_cleanup_task.cancel()
        try:
            await _support_cleanup_task
        except asyncio.CancelledError:
            pass
        _support_cleanup_task = None
    logger.info("Orchestrator Service shut down successfully")