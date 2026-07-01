"""
Data Handling Service - Main Application Entry Point
Handles data scraping, enrichment, scan execution, and findings management
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
from shared.utils import now_iso, hash_password, verify_password, SUPPORTED_COUNTRIES, DATA_BROKERS, PLANS
from shared.secrets_manager import init_infisical, get_cors_allowed_origins

# Initialize Infisical before importing routes to ensure module-level config can read loaded secrets.
init_infisical()

# Import local routers
from .routes import scan_router, findings_router, keywords_router, broker_router

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("data_handling")

CORS_ALLOWED_ORIGINS = get_cors_allowed_origins()
STARTED_AT = now_iso()

# Create FastAPI app
app = FastAPI(
    title="Data Handling Service",
    description="Data scraping, enrichment, scan execution, and findings management service",
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
app.include_router(scan_router, prefix="/api/scan", tags=["scanning"])
app.include_router(findings_router, prefix="/api/findings", tags=["findings"])
app.include_router(keywords_router, prefix="/api/keywords", tags=["keywords"])
app.include_router(broker_router, prefix="/api/brokers", tags=["brokers"])

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "service": "data_handling",
        "status": "healthy",
        "version": app.version,
        "started_at": STARTED_AT,
        "timestamp": now_iso()
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "data_handling",
        "version": "1.0.0",
        "description": "Data scraping, enrichment, scan execution, and findings management service",
        "endpoints": {
            "health": "/health",
            "scan": "/api/scan",
            "findings": "/api/findings",
            "keywords": "/api/keywords",
            "brokers": "/api/brokers"
        }
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Data Handling Service starting up...")
    init_infisical()
    logger.info("Data Handling Service started successfully")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Data Handling Service shutting down...")
    logger.info("Data Handling Service shut down successfully")