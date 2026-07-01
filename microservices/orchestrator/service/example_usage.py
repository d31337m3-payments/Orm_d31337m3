"""
Example showing how to use the Orchestrator Service
Demonstrates service registration, discovery, and lifecycle management
"""

import sys
import httpx
import asyncio

# Add shared and service directories to path
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices/shared')
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices/orchestrator/service')

from shared.jwt_utils import create_service_token, verify_service_token
from shared.security_middleware import verify_service_request

async def example_service_registration():
    """Example of how a service would register with the orchestrator"""
    
    # Create a service-to-service token for the orchestrator
    token = create_service_token("client_index")
    print(f"Created service token for client_index: {token[:50]}...")
    
    # Example: Registering with the orchestrator
    registration_data = {
        "service_name": "client_index",
        "host": "localhost",
        "port": 8002,
        "health_endpoint": "/health",
        "metadata": {
            "version": "1.0.0",
            "description": "User authentication and profile management service"
        }
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://orchestrator:8006/api/services/register",  # Orchestrator endpoint
                json=registration_data,
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                print(f"Successfully registered client_index with orchestrator")
                print(f"Response: {response.json()}")
            else:
                print(f"Failed to register service: {response.status_code}")
                print(f"Response: {response.text}")
        except Exception as e:
            print(f"Error registering with orchestrator: {e}")

async def example_service_discovery():
    """Example of how to discover services through the orchestrator"""
    
    # Create a service-to-service token
    token = create_service_token("client_index")
    print(f"Created service token for client_index: {token[:50]}...")
    
    # Example: Getting list of services from the orchestrator
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "http://orchestrator:8006/api/services/",  # Orchestrator endpoint
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                services_data = response.json()
                print(f"Discovered {services_data['count']} services:")
                for service in services_data['services']:
                    print(f"  - {service['service_name']}: {service['host']}:{service['port']} ({service['status']})")
            else:
                print(f"Failed to get services list: {response.status_code}")
        except Exception as e:
            print(f"Error discovering services: {e}")

async def example_health_check():
    """Example of how to check the orchestrator's health"""
    
    # Create a service-to-service token
    token = create_service_token("client_index")
    
    # Example: Checking orchestrator health
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "http://orchestrator:8006/api/health/",  # Orchestrator health endpoint
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                health_data = response.json()
                print(f"Orchestrator health: {health_data['status']}")
                print(f"Registered services: {health_data['registered_services']}")
                print(f"Healthy services: {health_data['healthy_services']}")
            else:
                print(f"Failed to get orchestrator health: {response.status_code}")
        except Exception as e:
            print(f"Error checking orchestrator health: {e}")

def print_service_info():
    """Print information about the service configuration"""
    print("=== Orchestrator Service Configuration ===")
    print(f"Service JWT Secret Configured: {'YES' if ORCHESTRATOR_JWT_SECRET != 'change-me-in-production' else 'NO (using default)'}")
    print(f"Client Index JWT Secret Configured: {'YES' if CLIENT_INDEX_JWT_SECRET != 'change-me-in-production' else 'NO (using default)'}")
    print("========================================")

if __name__ == "__main__":
    print_service_info()
    
    # Run async examples
    asyncio.run(example_service_registration())
    asyncio.run(example_service_discovery())
    asyncio.run(example_health_check())