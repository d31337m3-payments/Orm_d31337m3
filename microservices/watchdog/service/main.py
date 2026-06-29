"""
Watchdog Service - Main Application Entry Point
Handles service health monitoring, metrics collection, and alerting
"""

import os
import logging
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import shared components
import sys
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices/shared')

from shared.jwt_utils import create_service_token, verify_service_token, create_user_token, verify_user_token
from shared.security_middleware import verify_service_request, verify_user_request, require_service_auth, require_user_auth
from shared.database_models import *
from shared.utils import now_iso, hash_password, verify_password, SUPPORTED_COUNTRIES
from shared.secrets_manager import init_infisical

# Initialize Infisical before importing routes to ensure module-level config can read loaded secrets.
init_infisical()

# Import local routers
from .routes import health_router, metrics_router, alert_router

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("watchdog")

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "https://d31337m3.com,https://www.d31337m3.com,http://localhost:3000,http://127.0.0.1:3000").split(",")
    if o.strip()
]

# Create FastAPI app
app = FastAPI(
    title="Watchdog Service",
    description="Service health monitoring, metrics collection, and alerting service",
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
app.include_router(health_router, prefix="/api/health", tags=["health"])
app.include_router(metrics_router, prefix="/api/metrics", tags=["metrics"])
app.include_router(alert_router, prefix="/api/alerts", tags=["alerts"])

# Background task for health monitoring
background_tasks = set()

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"service": "watchdog", "status": "healthy", "timestamp": now_iso()}

# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "watchdog",
        "version": "1.0.0",
        "description": "Service health monitoring, metrics collection, and alerting service",
        "endpoints": {
            "health": "/health",
            "service_health": "/api/health",
            "metrics": "/api/metrics",
            "alerts": "/api/alerts"
        }
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Watchdog Service starting up...")
    init_infisical()
    # Start background health monitoring task
    task = asyncio.create_task(monitor_services_health())
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    logger.info("Watchdog Service started successfully")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Watchdog Service shutting down...")
    # Cancel all background tasks
    for task in background_tasks:
        task.cancel()
    await asyncio.gather(*background_tasks, return_exceptions=True)
    background_tasks.clear()
    logger.info("Watchdog Service shut down successfully")

# Background health monitoring task
async def monitor_services_health():
    """Background task to monitor the health of all registered services"""
    # In a real implementation, this would:
    # 1. Get list of registered services from orchestrator
    # 2. Periodically check each service's health endpoint
    # 3. Record health metrics
    # 4. Trigger alerts for unhealthy services
    # 5. Store historical health data
    
    while True:
        try:
            logger.debug("Watchdog: Performing health check cycle")
            # Health check logic would go here
            await asyncio.sleep(30)  # Check every 30 seconds
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in health monitoring: {e}")
            await asyncio.sleep(5)  # Short delay before retry