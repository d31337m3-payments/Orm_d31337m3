#!/bin/bash
# Startup script for Auditor Service

echo "Starting Auditor Service..."

# Set environment variables (in production, these would come from a secure vault)
export AUDITOR_JWT_SECRET=${AUDITOR_JWT_SECRET:-"dev-secret-change-in-production"}
export CLIENT_INDEX_JWT_SECRET=${CLIENT_INDEX_JWT_SECRET:-"dev-secret-change-in-production"}
export JWT_SECRET=${JWT_SECRET:-"dev-secret-change-in-production"}
export JWT_ALGORITHM=${JWT_ALGORITHM:-"HS256"}
export ACCESS_TOKEN_EXPIRE_MINUTES=${ACCESS_TOKEN_EXPIRE_MINUTES:-"1440"}

# Service port
export SERVICE_PORT=${SERVICE_PORT:-"8005"}

# Start the service
echo "Starting Auditor Service on port $SERVICE_PORT"
uvicorn service.main:app --host 0.0.0.0 --port $SERVICE_PORT --reload