"""
Example showing how to use the Client Index Service
Demonstrates service-to-service authentication and API usage
"""

import os
import sys
import httpx
import asyncio

# Add shared and service directories to path
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices/shared')
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices/client_index/service')

from shared.jwt_utils import create_service_token, verify_service_token
from shared.security_middleware import verify_service_request

# Service-specific secrets (should come from environment variables in production)
CLIENT_INDEX_JWT_SECRET = os.environ.get("CLIENT_INDEX_JWT_SECRET", "change-me-in-production")
ORCHESTRATOR_JWT_SECRET = os.environ.get("ORCHESTRATOR_JWT_SECRET", "change-me-in-production")

async def example_service_to_service_call():
    """Example of how client_index service would communicate with other services"""
    
    # Create a service-to-service token for outgoing requests
    token = create_service_token("client_index")
    print(f"Created service token for client_index: {token[:50]}...")
    
    # Example: Calling another service (e.g., payments)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://payments:8001/api/payments/verify",  # Example endpoint
                json={"user_id": "some-user-id", "amount": 100},
                headers={"Authorization": f"Bearer {token}"}
            )
            print(f"Response from payments service: {response.status_code}")
        except Exception as e:
            print(f"Error calling payments service: {e}")

async def example_internal_usage():
    """Example of how to use the service internally"""
    
    # Verify a service token (incoming request)
    # This would typically be done in a FastAPI dependency
    sample_token = create_service_token("orchestrator")
    try:
        payload = verify_service_token(sample_token, expected_issuer="orchestrator")
        print(f"Verified token from orchestrator: {payload}")
    except Exception as e:
        print(f"Token verification failed: {e}")
    
    # Create a user token
    user_token = create_user_token("user-123", False, "client_index")
    print(f"Created user token: {user_token[:50]}...")
    
    # Verify user token
    try:
        user_payload = verify_user_token(user_token)
        print(f"Verified user token: {user_payload}")
    except Exception as e:
        print(f"User token verification failed: {e}")

def print_service_info():
    """Print information about the service configuration"""
    print("=== Client Index Service Configuration ===")
    print(f"Service JWT Secret Configured: {'YES' if CLIENT_INDEX_JWT_SECRET != 'change-me-in-production' else 'NO (using default)'}")
    print(f"Orchestrator JWT Secret Configured: {'YES' if ORCHESTRATOR_JWT_SECRET != 'change-me-in-production' else 'NO (using default)'}")
    print("========================================")

if __name__ == "__main__":
    print_service_info()
    
    # Run async examples
    asyncio.run(example_service_to_service_call())
    asyncio.run(example_internal_usage())