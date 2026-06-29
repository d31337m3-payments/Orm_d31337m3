# Security Implementation Guide for Microservices

## Stage 2: Establish Security Boundaries

### 1. Isolate Credentials and Secrets Per Service

Each service should have its own JWT secret for service-to-service authentication:

```bash
# Environment variables for each service
export CLIENT_INDEX_JWT_SECRET="unique_secret_for_client_index_service"
export PAYMENTS_JWT_SECRET="unique_secret_for_payments_service"
export DATA_HANDLING_JWT_SECRET="unique_secret_for_data_handling_service"
export AUDITOR_JWT_SECRET="unique_secret_for_auditor_service"
export WATCHDOG_JWT_SECRET="unique_secret_for_watchdog_service"
export ORCHESTRATOR_JWT_SECRET="unique_secret_for_orchestrator_service"
```

### 2. Use Secure Credential Storage

For production deployment, secrets should be stored in a secure vault:

#### Options for Secure Secret Storage:
- **Infisical** - Open-source secret management platform (integrated)
- **HashiCorp Vault** - Industry standard for secret management
- **AWS Secrets Manager** - If deployed on AWS
- **Azure Key Vault** - If deployed on Azure
- **Google Cloud Secret Manager** - If deployed on GCP
- **Kubernetes Secrets** - If deployed on Kubernetes

#### Infisical Integration (Default):

Each service uses `shared/secrets_manager.py` to fetch secrets from Infisical at startup.

**Setup Steps:**

1. Create an Infisical account at https://app.infisical.com and create a project.

2. Generate a service token or machine identity in Infisical with read access to secrets.

3. Add secrets to your Infisical project for each service:
```
CLIENT_INDEX_JWT_SECRET     → unique_secret_for_client_index
PAYMENTS_JWT_SECRET         → unique_secret_for_payments
DATA_HANDLING_JWT_SECRET    → unique_secret_for_data_handling
AUDITOR_JWT_SECRET          → unique_secret_for_auditor
WATCHDOG_JWT_SECRET         → unique_secret_for_watchdog
ORCHESTRATOR_JWT_SECRET     → unique_secret_for_orchestrator
JWT_SECRET                  → legacy_shared_secret
JWT_ALGORITHM               → HS256
ACCESS_TOKEN_EXPIRE_MINUTES → 1440
```

4. Configure each service with the Infisical service token:
```bash
export INFISICAL_SITE_URL="https://app.infisical.com"
export INFISICAL_SERVICE_TOKEN="st.xxxx.your-service-token"
export INFISICAL_PROJECT_ID="your-project-id"
export INFISICAL_ENVIRONMENT="prod"
```

5. Start the service — it will fetch secrets from Infisical on startup and cache them.

**Architecture:**
- `shared/secrets_manager.py` — Infisical client wrapper with caching
- `init_infisical()` — Called on service startup, loads all secrets into cache
- `get_secret(key, default)` — Retrieves secrets from cache, falls back to env vars
- Falls back gracefully to environment variables if Infisical is unreachable

#### Example with HashiCorp Vault:
```bash
# Store secrets in Vault
vault kv put secret/microservices/client_index jwt_secret="your-secret-here"
vault kv put secret/microservices/payments jwt_secret="your-secret-here"
# ... repeat for each service

# Retrieve secrets in application
export CLIENT_INDEX_JWT_SECRET=$(vault kv get -field=jwt_secret secret/microservices/client_index)
```

### 3. Add Service-to-Service Auth Using JWT Tokens

All inter-service communication should use JWT tokens:

#### Token Creation (using shared/jwt_utils.py):
```python
from shared.jwt_utils import create_service_token

# Create a service-to-service token
token = create_service_token("client_index")
```

#### Token Verification (using shared/security_middleware.py):
```python
from shared.security_middleware import verify_service_request
from fastapi import Security, HTTPAuthorizationCredentials

async def protected_endpoint(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)
):
    # This will verify the token and return payload if valid
    payload = await verify_service_request(credentials, expected_service="payments")
    # Process request...
```

### 4. Ensure Audit Writes to Auditor Are Authenticated and Append-Only

The auditor service should:
- Only accept writes from authenticated services
- Validate that incoming tokens are from authorized services
- Store audit records with service identity in the `iss` field
- Implement write-once storage (no updates/deletes allowed)

#### Auditor Service Protection:
```python
# In auditor service endpoints
async def record_audit_event(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)
):
    # Verify the calling service is authorized to write audit events
    payload = await verify_service_request(credentials)
    
    # Log which service made the audit entry
    service_name = payload.get("iss")
    # Store audit record with service identity
```

### 5. Service-to-Service Communication Patterns

#### Internal Service Calls:
```python
import httpx
from shared.jwt_utils import create_service_token

async def call_internal_service(target_service: str, endpoint: str, data: dict):
    # Create token for outgoing request
    token = create_service_token("client_index")  # Current service name
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://{target_service}:800{target_service_port}{endpoint}",
            json=data,
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()
```

### 6. Implementation Checklist

For each service, ensure:
- [ ] Service-specific JWT secret configured in Infisical
- [ ] `init_infisical()` called in startup event
- [ ] Shared JWT utilities imported and used
- [ ] Security middleware applied to appropriate endpoints
- [ ] Public endpoints marked as such (registration, login, webhooks)
- [ ] User-facing endpoints require user authentication
- [ ] Service-to-service endpoints require service authentication
- [ ] Auditor service validates all incoming write requests
- [ ] All secrets stored securely in Infisical (not in code or plain env vars in prod)
- [ ] `INFISICAL_SERVICE_TOKEN` provided at runtime (not hardcoded)

### 7. Next Steps (Stage 3)

After establishing security boundaries, proceed to:
- Finalize service package boundaries for all microservices
- Extract shared libraries into common packages
- Keep orchestrator as the only API ingress coordination layer
- Continue hardening individual services starting with client_index

