# Launch Audit Checklist (Microservices-Only)

This checklist is the final go-live and audit evidence artifact for the current repository state.

## Topology Confirmation

- Public ingress: Nginx
- API ingress: orchestrator at 127.0.0.1:8006
- Internal services:
  - client_index: 8002
  - payments: 8003
  - data_handling: 8004
  - auditor: 8005
  - watchdog: 8007
  - support_hub: 8008
  - workforce_ops: 8009

## Monolith Removal Verification

- Legacy backend directory removed from repository.
- Rollback path is microservices-only (no fallback to legacy port 8001).
- Repository docs/configs scrubbed of monolith and legacy 8001 references.

## Secrets and Configuration Controls

- Secrets loading: Infisical-first via shared/secrets_manager.py
- Fallback path: environment variables
- Required Infisical runtime controls:
  - INFISICAL_PROJECT_ID
  - INFISICAL_ENVIRONMENT
  - INFISICAL_SERVICE_TOKEN or INFISICAL_CLIENT_ID + INFISICAL_CLIENT_SECRET
- Service persistence keys (local defaults, override via env/Infisical):
  - ORCHESTRATOR_SUPPORT_DB_PATH
  - PAYMENTS_DB_PATH
  - DATA_HANDLING_DB_PATH
  - WATCHDOG_DB_PATH
  - AUDITOR_DB_PATH

## Placeholder Closure Status

- Watchdog:
  - real health probing
  - persistence-backed metrics
  - persistence-backed alerts and resolution
- Auditor:
  - persistence-backed audit entries
  - compliance reporting with period filtering
  - real CSV export response
- Orchestrator:
  - implemented service health helper
  - implemented startup sequence helper

## Operational Gates

Run and capture outputs:

```bash
bash microservices/gate_check.sh
python3 -m py_compile \
  microservices/orchestrator/service/main.py \
  microservices/orchestrator/service/routes.py \
  microservices/client_index/service/main.py \
  microservices/payments/service/main.py \
  microservices/payments/service/routes.py \
  microservices/data_handling/service/main.py \
  microservices/data_handling/service/routes.py \
  microservices/watchdog/service/main.py \
  microservices/watchdog/service/routes.py \
  microservices/auditor/service/main.py \
  microservices/support_hub/service/main.py \
  microservices/workforce_ops/service/main.py
```

## Go/No-Go Sign-Off

- [ ] Gate check passes
- [ ] Critical flows validated (auth, payments, audit ingest)
- [ ] No P0/P1 incidents open
- [ ] Rollback script validated in staging
- [ ] Secrets loaded from Infisical in runtime environment
- [ ] Launch decision recorded with approvers
