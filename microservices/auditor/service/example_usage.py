"""
Example showing how to use the Auditor Service
Demonstrates audit trail recording and compliance reporting
"""

import os
import sys
import httpx
import asyncio

# Add shared and service directories to path
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices/shared')
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices/auditor/service')

from shared.jwt_utils import create_service_token, verify_service_token
from shared.security_middleware import verify_service_request

# Service-specific secrets (should come from environment variables in production)
AUDITOR_JWT_SECRET = os.environ.get("AUDITOR_JWT_SECRET", "change-me-in-production")
CLIENT_INDEX_JWT_SECRET = os.environ.get("CLIENT_INDEX_JWT_SECRET", "change-me-in-production")

async def example_audit_recording():
    """Example of how to record audit events through the auditor service"""
    
    # Create a service-to-service token for the auditor service
    token = create_service_token("auditor")
    print(f"Created service token for auditor: {token[:50]}...")
    
    print("\n=== Audit Recording Example ===")
    print("To record an audit event, you would:")
    print("1. Create a service-to-service token (via shared/jwt_utils.py)")
    print("2. Call POST /api/audit/record/ with audit event data")
    print("3. Service validates the calling service is authorized")
    print("4. Audit entry is stored with timestamp and metadata")
    print("5. Entry is append-only and tamper-evident")
    print("6. Service receives confirmation with audit ID")
    print("================================")

async def example_compliance_reporting():
    """Example of how to generate compliance reports through the auditor service"""
    
    # Create a service-to-service token
    token = create_service_token("auditor")
    print(f"Created service token for auditor: {token[:50]}...")
    
    print("\n=== Compliance Reporting Example ===")
    print("To generate a compliance report, you would:")
    print("1. Authenticate as an authorized user or service")
    print("2. Call GET /api/compliance/report/ with parameters")
    print("3. Specify report type (summary, detailed, etc.)")
    print("4. Specify period (7d, 30d, 90d, etc.)")
    print("5. Service generates statistics from audit logs")
    print("6. Report includes event breakdowns and trends")
    print("7. Data can be exported in JSON or CSV format")
    print("================================")

async def example_service_integration():
    """Example of how other services integrate with the auditor service"""
    
    print("\n=== Service Integration Example ===")
    print("Other services record audit events by:")
    print("1. Using helper functions from shared modules")
    print("2. Or making direct HTTP calls to auditor service")
    print("3. Recording user actions (logins, profile updates, etc.)")
    print("4. Recording system events (scan starts, payment processed, etc.)")
    print("5. Recording security events (failed logins, removal requests, etc.)")
    print("6. All entries are immutable and timestamped")
    print("7. Auditor service provides centralized audit trail")
    print("================================")

def print_service_info():
    """Print information about the service configuration"""
    print("=== Auditor Service Configuration ===")
    print(f"Service JWT Secret Configured: {'YES' if AUDITOR_JWT_SECRET != 'change-me-in-production' else 'NO (using default)'}")
    print(f"Client Index JWT Secret Configured: {'YES' if CLIENT_INDEX_JWT_SECRET != 'change-me-in-production' else 'NO (using default)'}")
    print("========================================")

if __name__ == "__main__":
    print_service_info()
    
    # Run async examples
    asyncio.run(example_audit_recording())
    asyncio.run(example_compliance_reporting())
    asyncio.run(example_service_integration())