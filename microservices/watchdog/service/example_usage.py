"""
Example showing how to use the Watchdog Service
Demonstrates service health monitoring, metrics collection, and alerting
"""

import sys
import httpx
import asyncio

# Add shared and service directories to path
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices/shared')
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices/watchdog/service')

from shared.jwt_utils import create_service_token, verify_service_token
from shared.security_middleware import verify_service_request

async def example_health_monitoring():
    """Example of how to monitor service health through the watchdog service"""
    
    # Create a service-to-service token for the watchdog service
    token = create_service_token("watchdog")
    print(f"Created service token for watchdog: {token[:50]}...")
    
    print("\n=== Health Monitoring Example ===")
    print("To monitor service health, you would:")
    print("1. Create a service-to-service token (via shared/jwt_utils.py)")
    print("2. Call GET /api/health/services/ to check all services")
    print("3. Call GET /api/health/{service_name}/ for specific service details")
    print("4. Watchdog performs active health checks on registered services")
    print("5. Response includes status, response time, and detailed metrics")
    print("6. Historical health data is stored for trend analysis")
    print("7. Unhealthy services trigger automatic alerts")
    print("================================")

async def example_metrics_collection():
    """Example of how to collect metrics through the watchdog service"""
    
    # Create a service-to-service token
    token = create_service_token("watchdog")
    print(f"Created service token for watchdog: {token[:50]}...")
    
    print("\n=== Metrics Collection Example ===")
    print("To collect metrics, you would:")
    print("1. Call GET /api/metrics/ for system-wide metrics")
    print("2. Call GET /api/metrics/services/{service_name}/ for service-specific metrics")
    print("3. Watchdog collects performance, resource, and business metrics")
    print("4. Metrics include request rates, response times, error rates")
    print("5. Resource metrics include CPU, memory, and disk usage")
    print("6. Business metrics include user counts, transaction volumes")
    print("7. Data is stored historically for trend analysis and reporting")
    print("================================")

async def example_alerting_system():
    """Example of how the alerting system works"""
    
    # Create a service-to-service token
    token = create_service_token("watchdog")
    print(f"Created service token for watchdog: {token[:50]}...")
    
    print("\n=== Alerting System Example ===")
    print("The watchdog alerting system:")
    print("1. Continuously monitors service health and metrics")
    print("2. Evaluates conditions against predefined thresholds")
    print("3. Automatically creates alerts when issues are detected")
    print("4. Supports multiple alert types (performance, security, availability)")
    print("5. Allows manual alert creation for custom situations")
    print("6. Provides alert resolution workflow")
    print("7. Can be configured to send notifications (email, SMS, Slack)")
    print("8. Maintains alert history for post-incident analysis")
    print("================================")

async def example_integration_patterns():
    """Example of how services integrate with the watchdog service"""
    
    print("\n=== Integration Patterns Example ===")
    print("Services integrate with watchdog by:")
    print("1. Exposing health check endpoints (GET /health)")
    print("2. Reporting metrics through standard formats")
    print("3. Logging significant events for audit trail")
    print("4. Using helper functions to report health status")
    print("5. Relying on watchdog for centralized monitoring")
    print("6. Benefiting from cross-service correlation")
    print("7. Receiving automated alerts for issues")
    print("8. Using watchdog data for capacity planning")
    print("================================")

def print_service_info():
    """Print information about the service configuration"""
    print("=== Watchdog Service Configuration ===")
    print(f"Service JWT Secret Configured: {'YES' if WATCHDOG_JWT_SECRET != 'change-me-in-production' else 'NO (using default)'}")
    print(f"Client Index JWT Secret Configured: {'YES' if CLIENT_INDEX_JWT_SECRET != 'change-me-in-production' else 'NO (using default)'}")
    print("========================================")

if __name__ == "__main__":
    print_service_info()
    
    # Run async examples
    asyncio.run(example_health_monitoring())
    asyncio.run(example_metrics_collection())
    asyncio.run(example_alerting_system())
    asyncio.run(example_integration_patterns())