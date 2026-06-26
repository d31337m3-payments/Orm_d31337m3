"""
API Routes for Orchestrator Service
Contains service discovery, registration, and lifecycle management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
import os
import logging

# Import shared components
import sys
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices/shared')

from shared.jwt_utils import create_service_token, verify_service_token
from shared.security_middleware import verify_service_request, require_service_auth
from shared.database_models import generate_id, now_iso
from shared.utils import SUPPORTED_COUNTRIES

# Import local models (would be defined in a models.py file)
# For now, we'll define them inline

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("orchestrator.routes")

# Create routers
service_router = APIRouter()
health_router = APIRouter()

# Security schemes
# In a real implementation, these would be imported from security_middleware

# Service registry (in production, this would be more sophisticated and persistent)
SERVICE_REGISTRY: Dict[str, dict] = {}
SERVICE_STARTUP_ORDER = [
    "auditor",      # 1. Available for event recording
    "client_index", # 2. Identity and auth ready
    "data_handling",# 3. Data store ready
    "payments",     # 4. Billing flows ready
    "watchdog",     # 5. Monitoring can begin
    "orchestrator"  # 6. Coordinates the others and exposes global state
]

# Service health check intervals (in seconds)
HEALTH_CHECK_INTERVAL = 30

# Pydantic models for service registration
class ServiceRegistration(BaseModel):
    service_name: str
    host: str
    port: int
    health_endpoint: str = "/health"
    metadata: Optional[Dict[str, Any]] = None

class ServiceInfo(BaseModel):
    service_name: str
    host: str
    port: int
    status: str  # "starting", "healthy", "unhealthy", "stopping", "stopped"
    last_health_check: Optional[str] = None
    health_endpoint: str
    metadata: Optional[Dict[str, Any]] = None
    registered_at: str
    updated_at: str

class ServiceResponse(BaseModel):
    service_name: str
    host: str
    port: int
    status: str
    last_health_check: Optional[str] = None

# Helper functions
def is_service_authorized(service_name: str, token_payload: dict) -> bool:
    """Check if a service is authorized to perform an action"""
    # In a real implementation, this would check permissions/roles
    issuer = token_payload.get("iss")
    return issuer is not None  # Simplified for example

def get_next_service_to_start() -> Optional[str]:
    """Get the next service that should be started based on dependencies"""
    for service_name in SERVICE_STARTUP_ORDER:
        if service_name not in SERVICE_REGISTRY or SERVICE_REGISTRY[service_name].get("status") != "healthy":
            return service_name
    return None

# Service registration and discovery endpoints
@service_router.post("/register")
async def register_service(
    service_data: ServiceRegistration,
    background: BackgroundTasks,
    token: dict = Depends(verify_service_request)
):
    """Register a service with the orchestrator"""
    service_name = service_data.service_name
    
    # Verify the service is authorized to register (in a real implementation)
    # if not is_service_authorized(service_name, token):
    #     raise HTTPException(status_code=403, detail="Not authorized to register service")
    
    # Check if service is in the expected startup order
    if service_name not in SERVICE_STARTUP_ORDER:
        logger.warning(f"Service {service_name} is not in the predefined startup order")
    
    # Create service info
    service_info = ServiceInfo(
        service_name=service_name,
        host=service_data.host,
        port=service_data.port,
        status="starting",
        last_health_check=now_iso(),
        health_endpoint=service_data.health_endpoint,
        metadata=service_data.metadata or {},
        registered_at=now_iso(),
        updated_at=now_iso()
    )
    
    # Register the service
    SERVICE_REGISTRY[service_name] = service_info.dict()
    
    logger.info(f"Service registered: {service_name} at {service_data.host}:{service_data.port}")
    
    # Start health checking in background (in a real implementation)
    # background.add_task(health_check_service, service_name)
    
    # Check if we can start the next service in the sequence
    # background.add_task(check_startup_sequence)
    
    return {
        "message": f"Service {service_name} registered successfully",
        "service": service_info
    }

@service_router.get("/")
async def list_services(token: dict = Depends(verify_service_request)):
    """List all registered services"""
    services = []
    for service_name, service_info in SERVICE_REGISTRY.items():
        services.append(ServiceResponse(
            service_name=service_info["service_name"],
            host=service_info["host"],
            port=service_info["port"],
            status=service_info["status"],
            last_health_check=service_info["last_health_check"]
        ))
    
    return {
        "services": services,
        "count": len(services),
        "startup_order": SERVICE_STARTUP_ORDER
    }

@service_router.get("/{service_name}")
async def get_service(
    service_name: str,
    token: dict = Depends(verify_service_request)
):
    """Get information about a specific service"""
    if service_name not in SERVICE_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
    
    service_info = SERVICE_REGISTRY[service_name]
    return ServiceResponse(
        service_name=service_info["service_name"],
        host=service_info["host"],
        port=service_info["port"],
        status=service_info["status"],
        last_health_check=service_info["last_health_check"]
    )

@service_router.put("/{service_name}/heartbeat")
async def service_heartbeat(
    service_name: str,
    token: dict = Depends(verify_service_request)
):
    """Update service heartbeat (called by services to indicate they're healthy)"""
    if service_name not in SERVICE_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
    
    # Update service status to healthy
    SERVICE_REGISTRY[service_name]["status"] = "healthy"
    SERVICE_REGISTRY[service_name]["last_health_check"] = now_iso()
    SERVICE_REGISTRY[service_name]["updated_at"] = now_iso()
    
    logger.debug(f"Heartbeat received from {service_name}")
    
    return {
        "message": f"Heartbeat updated for {service_name}",
        "status": "healthy",
        "timestamp": now_iso()
    }

@service_router.put("/{service_name}/status")
async def update_service_status(
    service_name: str,
    status_update: dict,
    token: dict = Depends(verify_service_request)
):
    """Update service status (called by services or monitoring systems)"""
    if service_name not in SERVICE_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
    
    valid_statuses = ["starting", "healthy", "unhealthy", "stopping", "stopped"]
    if status_update.get("status") not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )
    
    # Update service status
    SERVICE_REGISTRY[service_name]["status"] = status_update["status"]
    SERVICE_REGISTRY[service_name]["last_health_check"] = now_iso() if status_update["status"] in ["healthy", "unhealthy"] else SERVICE_REGISTRY[service_name]["last_health_check"]
    SERVICE_REGISTRY[service_name]["updated_at"] = now_iso()
    
    logger.info(f"Service {service_name} status updated to: {status_update['status']}")
    
    return {
        "message": f"Service {service_name} status updated",
        "status": status_update["status"],
        "timestamp": now_iso()
    }

@service_router.delete("/{service_name}")
async def deregister_service(
    service_name: str,
    token: dict = Depends(verify_service_request)
):
    """Deregister a service from the orchestrator"""
    if service_name not in SERVICE_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
    
    # Remove service from registry
    deregistered_service = SERVICE_REGISTRY.pop(service_name)
    
    logger.info(f"Service deregistered: {service_name}")
    
    return {
        "message": f"Service {service_name} deregistered successfully",
        "service": deregistered_service
    }

# Health check endpoints for the orchestrator itself
@health_router.get("/")
async def orchestrator_health():
    """Get orchestrator health status"""
    healthy_services = sum(1 for service in SERVICE_REGISTRY.values() if service.get("status") == "healthy")
    total_services = len(SERVICE_REGISTRY)
    
    return {
        "service": "orchestrator",
        "status": "healthy",
        "timestamp": now_iso(),
        "registered_services": total_services,
        "healthy_services": healthy_services,
        "startup_order": SERVICE_STARTUP_ORDER,
        "next_service_to_start": get_next_service_to_start()
    }

@health_router.get("/startup-sequence")
async def get_startup_sequence(token: dict = Depends(verify_service_request)):
    """Get the current startup sequence status"""
    sequence_status = []
    for service_name in SERVICE_STARTUP_ORDER:
        if service_name in SERVICE_REGISTRY:
            service_info = SERVICE_REGISTRY[service_name]
            sequence_status.append({
                "service_name": service_name,
                "status": service_info["status"],
                "host": service_info["host"],
                "port": service_info["port"],
                "last_health_check": service_info["last_health_check"]
            })
        else:
            sequence_status.append({
                "service_name": service_name,
                "status": "not_registered",
                "host": None,
                "port": None,
                "last_health_check": None
            })
    
    return {
        "startup_order": SERVICE_STARTUP_ORDER,
        "sequence_status": sequence_status,
        "all_services_healthy": all(
            s.get("status") == "healthy" 
            for s in SERVICE_REGISTRY.values() 
            if s.get("service_name") in SERVICE_STARTUP_ORDER
        )
    }

# Background tasks (would be implemented in a real system)
async def health_check_service(service_name: str):
    """Periodically check the health of a registered service"""
    # This would make HTTP requests to the service's health endpoint
    # and update the service status accordingly
    pass

async def check_startup_sequence():
    """Check if services can be started in the correct sequence"""
    # This would implement the logic to start services in dependency order
    # based on health checks and readiness
    pass