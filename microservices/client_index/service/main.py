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
from shared.utils import now_iso, hash_password, verify_password, SUPPORTED_COUNTRIES, LEGAL_TEMPLATES, _fill_template

# Import local routers
from .routes import auth_router, user_router, profile_router

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("client_index")

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
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
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
    # In a real implementation, you would initialize database connections here
    logger.info("Client Index Service started successfully")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Client Index Service shutting down...")
    # In a real implementation, you would close database connections here
    logger.info("Client Index Service shut down successfully")