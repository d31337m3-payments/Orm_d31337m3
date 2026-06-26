#!/bin/bash
# Startup script for Client Index Service

echo "Starting Client Index Service..."

# Set environment variables (in production, these would come from a secure vault)
export CLIENT_INDEX_JWT_SECRET=${CLIENT_INDEX_JWT_SECRET:-"dev-secret-change-in-production"}
export ORCHESTRATOR_JWT_SECRET=${ORCHESTRATOR_JWT_SECRET:-"dev-secret-change-in-production"}
export JWT_SECRET=${JWT_SECRET:-"dev-secret-change-in-production"}
export JWT_ALGORITHM=${JWT_ALGORITHM:-"HS256"}
export ACCESS_TOKEN_EXPIRE_MINUTES=${ACCESS_TOKEN_EXPIRE_MINUTES:-"1440"}

# Database connection (would be configured per service in production)
export MONGO_URL=${MONGO_URL:-"mongodb://localhost:27017"}
export DB_NAME=${DB_NAME:-"d31337m3"}

# Service port
export SERVICE_PORT=${SERVICE_PORT:-"8002"}

# Start the service
echo "Starting Client Index Service on port $SERVICE_PORT"
uvicorn service.main:app --host 0.0.0.0 --port $SERVICE_PORT --reload