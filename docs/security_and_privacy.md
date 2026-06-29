# Security and Privacy

This document summarizes security controls and privacy protections aligned with the current implementation.

## Current Architecture Context

- Public ingress: Nginx
- Frontend: React app on `127.0.0.1:3000`
- API ingress: orchestrator on `127.0.0.1:8006`
- Internal microservices:
  - `client_index` (`8002`)
  - `payments` (`8003`)
  - `data_handling` (`8004`)
  - `auditor` (`8005`)
  - `watchdog` (`8007`)

## Core Security Controls

- HTTPS termination and certificate management via Nginx + Certbot.
- Service isolation by role (identity, payments, data, audit, telemetry).
- Dedicated startup and health gates (`microservices/gate_check.sh`).
- Rollback command pack (`microservices/rollback.sh`).
- Audit-focused service (`auditor`) for operational traceability.
- Password hashing and JWT-based auth flow in service layer.

## Network and Access Controls

- Only Nginx should be internet-exposed.
- Microservice ports should remain host-internal/private.
- Use host firewall rules (UFW/security groups) to block direct public access to service ports.
- Restrict administrative access (SSH, systemd controls, deployment scripts).

## Secrets and Configuration

- Keep secrets out of Git.
- Use environment variables or a managed secrets platform.
- Replace all development defaults before production cutover.
- Rotate JWT/signing credentials and external provider keys regularly.

## Privacy Practices

- Minimize stored personal data.
- Encrypt data at rest/in transit where applicable.
- Limit staff access to customer data and log admin actions.
- Define retention and deletion workflows for customer records.

## Logging and Monitoring

- Keep structured logs for each service and Nginx.
- Monitor auth failures, payment failures, and service health transitions.
- Alert on sustained 5xx, service unavailability, and audit pipeline failures.

## Operational Security Checklist

- [ ] HTTPS active for all public domains.
- [ ] Nginx security headers configured.
- [ ] Firewall blocks direct service-port access.
- [ ] All systemd units enabled and healthy.
- [ ] Gate check passes before deployments.
- [ ] Rollback procedure tested.
- [ ] Backup and restore process validated.

## Incident Handling

- Trigger rollback for major auth/payment/audit failures.
- Preserve logs and timeline immediately.
- Perform root-cause analysis and corrective action review.
