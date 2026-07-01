"""
Support Hub Service - Main Application Entry Point
Handles live support chat sessions and trouble tickets.
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

from .routes import support_router

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("support_hub")

CORS_ALLOWED_ORIGINS = get_cors_allowed_origins()
STARTED_AT = now_iso()

app = FastAPI(
    title="Support Hub Service",
    description="Live support chat and trouble ticket management",
    version="1.0.5",
)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(support_router, prefix="/api/support", tags=["support"])


@app.get("/health")
async def health_check():
    return {
        "service": "support_hub",
        "status": "healthy",
        "version": app.version,
        "started_at": STARTED_AT,
        "timestamp": now_iso()
    }


@app.get("/")
async def root():
    return {
        "service": "support_hub",
        "version": "1.0.0",
        "description": "Live support chat and trouble ticket management",
        "endpoints": {
            "health": "/health",
            "support": "/api/support",
        },
    }


@app.on_event("startup")
async def startup_event():
    logger.info("Support Hub Service starting up...")
    init_infisical()
    logger.info("Support Hub Service started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Support Hub Service shutting down...")
    logger.info("Support Hub Service shut down successfully")
