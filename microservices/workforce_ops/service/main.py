"""
Workforce Ops Service - Main Application Entry Point
Handles employee scheduling, time tracking, and payroll runs.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import sys
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices/shared')

from shared.database_models import now_iso
from shared.secrets_manager import init_infisical, get_cors_allowed_origins

# Initialize Infisical before importing routes to ensure module-level config can read loaded secrets.
init_infisical()

from .routes import workforce_router

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("workforce_ops")

CORS_ALLOWED_ORIGINS = get_cors_allowed_origins()
STARTED_AT = now_iso()

app = FastAPI(
    title="Workforce Ops Service",
    description="Employee scheduling and payroll operations",
    version="1.0.5",
)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workforce_router, prefix="/api/workforce", tags=["workforce"])


@app.get("/health")
async def health_check():
    return {
        "service": "workforce_ops",
        "status": "healthy",
        "version": app.version,
        "started_at": STARTED_AT,
        "timestamp": now_iso()
    }


@app.get("/")
async def root():
    return {
        "service": "workforce_ops",
        "version": "1.0.0",
        "description": "Employee scheduling and payroll operations",
        "endpoints": {
            "health": "/health",
            "workforce": "/api/workforce",
        },
    }


@app.on_event("startup")
async def startup_event():
    logger.info("Workforce Ops Service starting up...")
    init_infisical()
    logger.info("Workforce Ops Service started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Workforce Ops Service shutting down...")
    logger.info("Workforce Ops Service shut down successfully")
