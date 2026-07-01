"""
Example showing how to use the Data Handling Service
Demonstrates data scraping, scan execution, and findings management
"""

import sys
import httpx
import asyncio

# Add shared and service directories to path
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices/shared')
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices/data_handling/service')

from shared.jwt_utils import create_service_token, verify_service_token
from shared.security_middleware import verify_service_request



async def example_scanning():
    """Example of how to trigger a scan through the data handling service"""
    
    # Create a service-to-service token for the data handling service
    token = create_service_token("data_handling")
    print(f"Created service token for data_handling: {token[:50]}...")
    
    print("\n=== Scanning Example ===")
    print("To run a scan, you would:")
    print("1. Authenticate the user (via client_index service)")
    print("2. Call POST /api/scan/run/ to trigger a scan")
    print("3. Service queues the scan in the background")
    print("4. System performs real HTTP crawling across data brokers")
    print("5. Results are enriched with realistic data for demo purposes")
    print("6. New findings are stored and user is notified via email")
    print("7. User can review findings in their dashboard")
    print("================================")

async def example_findings_management():
    """Example of how to manage findings through the data handling service"""
    
    # Create a service-to-service token
    token = create_service_token("data_handling")
    print(f"Created service token for data_handling: {token[:50]}...")
    
    print("\n=== Findings Management Example ===")
    print("To manage findings, you would:")
    print("1. Authenticate the user (via client_index service)")
    print("2. Call GET /api/findings/ to list all findings")
    print("3. Review findings details (broker, URL, data found, severity)")
    print("4. Call POST /api/findings/removal-request to request removal")
    print("5. System updates finding status to pending_removal")
    print("6. Auditor service logs the removal request")
    print("7. Watchdog service monitors the process")
    print("================================")

async def example_keyword_management():
    """Example of how to manage keywords through the data handling service"""
    
    # Create a service-to-service token
    token = create_service_token("data_handling")
    print(f"Created service token for data_handling: {token[:50]}...")
    
    print("\n=== Keyword Management Example ===")
    print("To manage keywords, you would:")
    print("1. Authenticate the user (via client_index service)")
    print("2. Call GET /api/keywords/ to list monitored keywords")
    print("3. Call POST /api/keywords/ to add new keywords to monitor")
    print("4. Call DELETE /api/keywords/{id} to remove keywords")
    print("5. System tracks last scan time for each keyword")
    print("6. Scans respect user's subscription limits")
    print("================================")

async def example_broker_integration():
    """Example of how the data handling service integrates with data brokers"""
    
    print("\n=== Broker Integration Example ===")
    print("The data handling service performs:")
    print("- Real HTTP crawling across major data brokers:")
    print("  * Spokeo, WhitePages, FastPeopleSearch")
    print("  * Google & Bing search results (mention counting)")
    print("- Fallback to realistic enriched data for demo purposes")
    print("- Support for all monitored data types:")
    print("  * Name, Email, Phone, Address, Other")
    print("- Proper deduplication to avoid duplicate findings")
    print("- Severity assessment based on data type and source")
    print("================================")

def print_service_info():
    """Print information about the service configuration"""
    print("=== Data Handling Service Configuration ===")
    print(f"Service JWT Secret Configured: {'YES' if DATA_HANDLING_JWT_SECRET != 'change-me-in-production' else 'NO (using default)'}")
    print(f"Client Index JWT Secret Configured: {'YES' if CLIENT_INDEX_JWT_SECRET != 'change-me-in-production' else 'NO (using default)'}")
    print("========================================")

if __name__ == "__main__":
    print_service_info()
    
    # Run async examples
    asyncio.run(example_scanning())
    asyncio.run(example_findings_management())
    asyncio.run(example_keyword_management())
    asyncio.run(example_broker_integration())