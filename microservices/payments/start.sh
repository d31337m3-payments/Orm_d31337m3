#!/bin/bash
# Startup script for Payments Service

echo "Starting Payments Service..."

# Set environment variables (in production, these would come from a secure vault)
export PAYMENTS_JWT_SECRET=${PAYMENTS_JWT_SECRET:-"dev-secret-change-in-production"}
export CLIENT_INDEX_JWT_SECRET=${CLIENT_INDEX_JWT_SECRET:-"dev-secret-change-in-production"}
export JWT_SECRET=${JWT_SECRET:-"dev-secret-change-in-production"}
export JWT_ALGORITHM=${JWT_ALGORITHM:-"HS256"}
export ACCESS_TOKEN_EXPIRE_MINUTES=${ACCESS_TOKEN_EXPIRE_MINUTES:-"1440"}

# Payment-specific environment variables
export PAYMENTS_EMAIL=${PAYMENTS_EMAIL:-"payments@example.com"}
export CRYPTO_WALLET=${CRYPTO_WALLET:-"0x742d35Cc6634C0532925a3b8D4C0532950532950"}
export ETHEREUM_RPC_URL=${ETHEREUM_RPC_URL:-"https://mainnet.infura.io/v3/YOUR_INFURA_KEY"}
export POLYGON_RPC_URL=${POLYGON_RPC_URL:-"https://polygon-mainnet.infura.io/v3/YOUR_INFURA_KEY"}
export BASE_RPC_URL=${BASE_RPC_URL:-"https://mainnet.base.org"}
export USDC_ETHEREUM=${USDC_ETHEREUM:-"0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"}
export USDC_POLYGON=${USDC_POLYGON:-"0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"}
export USDC_BASE=${USDC_BASE:-"0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"}

# Service port
export SERVICE_PORT=${SERVICE_PORT:-"8003"}

# Start the service
echo "Starting Payments Service on port $SERVICE_PORT"
uvicorn service.main:app --host 0.0.0.0 --port $SERVICE_PORT --reload