"""\"\"
Example showing how to use the Payments Service
Demonstrates payment processing and subscription management
\"\"\"

import os
import sys
import httpx
import asyncio

# Add shared and service directories to path
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices/shared')
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices/payments/service')

from shared.jwt_utils import create_service_token, verify_service_token
from shared.security_middleware import verify_service_request

# Service-specific secrets (should come from environment variables in production)
PAYMENTS_JWT_SECRET = os.environ.get(\"PAYMENTS_JWT_SECRET\", \"change-me-in-production\")
CLIENT_INDEX_JWT_SECRET = os.environ.get(\"CLIENT_INDEX_JWT_SECRET\", \"change-me-in-production\")

async def example_payment_processing():
    \"\"\"Example of how to process a payment through the payments service\"\"\"
    
    # Create a service-to-service token for the payments service
    token = create_service_token(\"payments\")
    print(f\"Created service token for payments: {token[:50]}...\")
    
    # Example: Processing an Interac payment
    payment_data = {
        \"plan_id\": \"pro\",
        \"payment_method\": \"interac\",
        # Note: In a real implementation, user would be obtained from auth token
        # For this example, we're showing the structure
    }
    
    print(\"\\n=== Payment Processing Example ===\")
    print(\"To process a payment, you would:\")
    print(\"1. Authenticate the user (via client_index service)\")
    print(\"2. Call POST /api/payments/ with payment details\")
    print(\"3. Receive payment instructions for Interac, Stripe, or Crypto\")
    print(\"4. User completes payment according to instructions\")
    print(\"5. Admin confirms payment (for Interac) or system verifies (for Stripe/Crypto)\")
    print(\"6. User subscription is updated to active\")
    print(\"================================\")

async def example_subscription_management():
    \"\"\"Example of how to manage subscriptions through the payments service\"\"\"
    
    # Create a service-to-service token
    token = create_service_token(\"payments\")
    print(f\"Created service token for payments: {token[:50]}...\")
    
    print(\"\\n=== Subscription Management Example ===\")
    print(\"To manage subscriptions, you would:\")
    print(\"1. Authenticate the user (via client_index service)\")
    print(\"2. Call GET /api/subscriptions/ to get current subscription\")
    print(\"3. Call POST /api/subscriptions/ to change subscription plan\")
    print(\"4. System processes payment and updates subscription status\")
    print(\"5. User receives confirmation email\")
    print(\"================================\")

async def example_webhook_handling():
    \"\"\"Example of how webhooks work with the payments service\"\"\"
    
    print(\"\\n=== Webhook Handling Example ===\")
    print(\"The payments service provides webhook endpoints for:\")
    print(\"- Stripe: POST /api/webhooks/stripe\")
    print(\"- Interac: POST /api/webhooks/interac\")
    print(\"(In production, these would be configured with payment providers)\")
    print(\"Webhooks allow automatic payment status updates\")
    print(\"================================\")

def print_service_info():
    \"\"\"Print information about the service configuration\"\"\"
    print(\"=== Payments Service Configuration ===\")
    print(f\"Service JWT Secret Configured: {'YES' if PAYMENTS_JWT_SECRET != 'change-me-in-production' else 'NO (using default)'}\")
    print(f\"Client Index JWT Secret Configured: {'YES' if CLIENT_INDEX_JWT_SECRET != 'change-me-in-production' else 'NO (using default)'}\")
    print(\"========================================\")

if __name__ == \"__main__\":
    print_service_info()
    
    # Run async examples
    asyncio.run(example_payment_processing())
    asyncio.run(example_subscription_management())
    asyncio.run(example_webhook_handling())