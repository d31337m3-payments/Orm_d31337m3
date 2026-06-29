# Agent Go-Live Guideline for API Microservices

This guide is the execution playbook for the final steps to bring API microservices live and production ready.

Scope:
- `payments`
- `data_handling`
- `client_index`
- `auditor`
- `watchdog`
- `orchestrator` (ring leader)

## 1. Agent Operating Rules

1. Work in phases and do not skip gates.
2. Every gate requires proof artifacts (command output, logs, screenshots, metrics snapshots).
3. Never promote if any P0/P1 incident is open.
4. All production changes must be reversible within 5 minutes.
5. No direct database access across service boundaries.
6. Every sensitive action must emit an audit event to `auditor`.

## 2. Release Success Criteria

Deployment is successful only if all are true:
- Availability SLO met for 24h after cutover.
- Error rate below agreed threshold (example: < 1% 5xx).
- Auth flows succeed (`client_index`) and token validation works service-to-service.
- Trial-to-paid upgrade flow succeeds end-to-end in `payments`.
- `auditor` receives and stores append-only events from all services.
- `watchdog` health dashboard shows all services healthy.
- Rollback path tested and documented.

## 3. Environment and Infrastructure Baseline

Before release, confirm:
- Separate environments: `staging` and `production`.
- Service runtime isolation (containers or isolated processes).
- Private service network for internal traffic.
- Public ingress only through edge gateway / Nginx / orchestrator entrypoint.
- Centralized logs and metrics collection enabled.
- Secrets manager configured (no secrets in repo or plain files).

Required infra controls:
- TLS for external traffic.
- mTLS or signed service tokens for internal traffic.
- Network policy restricting east-west traffic to required pairs only.

## 4. Service-by-Service Production Readiness Checklist

### `client_index`
- Password hashing uses bcrypt/argon2.
- Session/token expiration and rotation configured.
- Rate limiting enabled on login endpoints.
- MFA hooks or roadmap path documented.
- PII encryption at rest enabled.

### `payments`
- Webhook signature validation enforced.
- Idempotency keys enabled for payment write operations.
- Trial upgrade activation tested with success and failure cases.
- Refund/cancel paths validated.
- Ledger-like transaction history immutable and auditable.

### `data_handling`
- Migrations versioned and tested.
- Scraping/indexing jobs isolated from user request path.
- Data retention and purge policies configured.
- Access to customer data limited by role and purpose.

### `auditor`
- Write-only event ingestion path in place.
- Immutable audit storage policy verified.
- Query API read access restricted by role.
- Tamper detection and event integrity checks active.

### `watchdog`
- Health probes defined for each service.
- Alerting routes configured (email/slack/pager).
- Auto-remediation actions guarded by cooldown and limits.

### `orchestrator`
- Startup ordering enforced by dependency graph.
- Readiness gates before routing traffic.
- Dynamic config and secret injection validated.
- Graceful shutdown and rolling restart behavior tested.

## 5. Pre-Go-Live Test Matrix (Must Pass)

### Functional
- User signup/login/logout.
- Password reset and token expiry.
- Trial account creation.
- Trial to paid conversion.
- Billing webhook processing.
- Data ingest/search/index retrieval.
- Audit trail visibility for all critical actions.

### Resilience
- Kill one service and confirm graceful degradation.
- Simulate DB restart and verify reconnect behavior.
- Simulate payment provider timeout and retry behavior.
- Confirm watchdog alert and orchestrator response.

### Security
- AuthZ checks across all privileged endpoints.
- Invalid token and expired token tests.
- Secret rotation test.
- TLS certificate validity check.
- Pen-test quick pass for obvious vulnerabilities.

## 6. Data Migration and Compatibility Plan

1. Freeze schema changes before migration window.
2. Take verified backup and restore test in staging.
3. Run forward migrations.
4. Validate record counts and checksums on critical tables.
5. Cut read path to orchestrator-routed microservices only after parity checks pass.

## 7. Deployment Strategy

Use progressive delivery:
1. Deploy to staging.
2. Run full integration suite.
3. Deploy production as dark launch (no user traffic).
4. Enable internal traffic only.
5. Canary: 5% traffic -> 25% -> 50% -> 100%.
6. Hold at each step for metrics observation.

Block promotion immediately if:
- 5xx spikes above threshold.
- Authentication failures increase significantly.
- Payment conversion errors increase.
- Audit event ingestion falls behind.

## 8. Cutover Runbook

### T-60 min
- Change freeze starts.
- Validate alerting and on-call assignments.
- Confirm rollback package/version available.

### T-30 min
- Validate health endpoints and dependencies.
- Verify certificates, DNS, and ingress.
- Snapshot baseline metrics.

### T-0
- Start canary routing.
- Watch SLO dashboards continuously.
- Confirm payment and login smoke tests in production.

### T+30 min
- Increase to 25% if stable.
- Re-run smoke tests and audit verification.

### T+60 min
- Increase to 50% then 100% if stable.
- Close deployment only after post-cutover checks pass.

## 9. Rollback Plan (Mandatory)

Rollback triggers:
- Sustained 5xx over threshold.
- Payment flow corruption risk.
- Authentication outage.
- Audit logging failure.

Rollback actions:
1. Route traffic back to previous stable stack.
2. Disable new writes if data integrity risk exists.
3. Restore from backup only if required and approved.
4. Publish incident report with timeline and root cause.

## 10. Observability Requirements

Minimum dashboards:
- Request rate, latency, error rate per service.
- Auth success/failure by endpoint.
- Payment success/failure and webhook lag.
- Queue/job lag for data pipelines.
- Audit ingest throughput and storage latency.

Required traces/log fields:
- `trace_id`, `request_id`, `user_id` (where applicable), `service`, `operation`, `status_code`.

## 11. Security and Privacy Go-Live Controls

- Enforce least privilege IAM roles for each service.
- Encrypt PII in transit and at rest.
- Mask/redact PII in application logs.
- Store secrets in a managed secret store.
- Confirm GDPR/CCPA request handling path (export/delete) is functional.
- Ensure employee/admin access to customer data is logged and reviewable.

## 12. Post-Go-Live (First 7 Days)

Day 0-1:
- Hourly metrics and incident review.
- Validate payments reconciliation daily.

Day 2-3:
- Tune autoscaling and alert thresholds.
- Review slow queries and hot endpoints.

Day 4-7:
- Run post-implementation review.
- Convert temporary exceptions into tracked backlog items.

## 13. Agent Deliverables Checklist

The agent must provide:
- Deployment summary by phase.
- Gate pass/fail report with evidence.
- Test matrix results.
- Security validation report.
- Rollback test proof.
- Final sign-off recommendation: `GO` or `NO-GO`.

## 14. GO / NO-GO Template

Use this template for final decision:

- Release version:
- Date/time:
- Services deployed:
- Gate status:
  - Infra: PASS/FAIL
  - Functional: PASS/FAIL
  - Security: PASS/FAIL
  - Resilience: PASS/FAIL
  - Observability: PASS/FAIL
- Known risks:
- Rollback readiness verified: YES/NO
- Final decision: GO/NO-GO
- Approvers:
