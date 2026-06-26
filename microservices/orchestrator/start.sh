#!/bin/bash
# Startup script for Orchestrator Service

echo "Starting Orchestrator Service..."

# Set environment variables (in production, these would come from a secure vault)
export ORCHESTRATOR_JWT_SECRET=${ORCHESTRATOR_JWT_SECRET:-"dev-secret-change-in-production"}
export CLIENT_INDEX_JWT_SECRET=${CLIENT_INDEX_JWT_SECRET:-"dev-secret-change-in-production"}
export JWT_SECRET=${JWT_SECRET:-"dev-secret-change-in-production"}
export JWT_ALGORITHM=${JWT_ALGORITHM:-"HS256"}
export ACCESS_TOKEN_EXPIRE_MINUTES=${ACCESS_TOKEN_EXPIRE_MINUTES:-"1440"}

# Service port
export SERVICE_PORT=${SERVICE_PORT:-"8006"}

# Start the service
echo "Starting Orchestrator Service on port $SERVICE_PORT"
uvicorn service.main:app --host 0.0.0.0 --port $SERVICE_PORT --reload