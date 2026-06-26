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

from shared.jwt_utils import create_service_token, verify_service_token
from shared.security_middleware import verify_service_request, require_service_auth
from shared.database_models import generate_id, now_iso
from shared.utils import SUPPORTED_COUNTRIES

# Import local routers
from .routes import service_router, health_router

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("orchestrator")

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
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(service_router, prefix="/api/services", tags=["services"])
app.include_router(health_router, prefix="/api/health", tags=["health"])

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
    logger.info("Orchestrator Service starting up...")
    logger.info(f"Service startup order: {SERVICE_STARTUP_ORDER}")
    logger.info("Orchestrator Service started successfully")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Orchestrator Service shutting down...")
    logger.info("Orchestrator Service shut down successfully")