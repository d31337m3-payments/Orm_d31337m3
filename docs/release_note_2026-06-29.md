# Release Note — 2026-06-29

## Release ID

- Commit: 8f1fc2649ead721d349e7d693ed3136f3bd6c499
- Branch: main
- Title: Finalize microservices-only launch readiness and audit hardening
- Author: admin <admin@d31337m3.com>

## Executive Summary

This release finalizes the migration to a microservices-only production topology, removes the legacy monolith from runtime and repository usage, closes remaining high-impact placeholders with real functionality, and adds launch/audit evidence artifacts.

## Scope of Change

- 57 files changed
- 4001 insertions
- 3138 deletions

## What Shipped

1. Monolith removal and topology enforcement
- Legacy backend directory removed from repository.
- Rollback behavior converted to microservices-only flow.
- Nginx/API routing normalization aligned to orchestrator ingress on 8006.

2. Secrets and configuration hardening
- Infisical-first runtime loading ensured before route-module imports in services.
- Runtime config resolution fixed where import-time defaults could bypass secret loading.
- Service persistence/env keys normalized and documented.

3. Placeholder closure with real functionality
- Watchdog now performs real health probing and persistence-backed metrics/alerts.
- Auditor now persists audit entries and provides real CSV export.
- Orchestrator helper flows for health checks/startup sequencing implemented.

4. Frontend integration and stability
- API base URL resolution corrected for deployment env precedence.
- Admin/security/support integration updates shipped.
- Frontend production build compiles successfully.

5. Operations and audit docs
- Added launch audit artifact: docs/launch_audit_checklist.md
- Documentation scrubbed for monolith/legacy runtime references.

## Validation Evidence

- Gate check: passed (all core services healthy, orchestrator API root check passed, nginx routing check passed).
- Python compile checks: passed for touched microservice modules.
- Frontend build: compiled successfully.

## Operational Readiness Notes

- Production path is microservices-only.
- Rollback script remains available but no longer routes to legacy backend.
- Secrets are expected from Infisical with env fallback for controlled operations.

## Auditor Sign-Off Checklist

- [x] Monolith runtime path removed
- [x] Microservices gate check green
- [x] Secrets loading path documented
- [x] Launch audit checklist present
- [x] Release committed and pushed to origin/main
