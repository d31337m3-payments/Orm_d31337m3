# Roadmap

This roadmap reflects the current microservices-based implementation.

## Near Term (0-3 months)

- Operational hardening
  - Finalize production runbooks and on-call handoff
  - Add CI checks for microservices/frontend builds and smoke tests
  - Validate backup/restore and rollback drills
- Admin control surface
  - Continue expanding admin operations for service and payment workflows
  - Improve telemetry visibility and incident diagnostics

## Mid Term (3-9 months)

- Reliability and scale
  - Add stronger observability (metrics, tracing, alert routing)
  - Improve service resilience and graceful degradation patterns
- Security maturity
  - Secrets lifecycle automation and periodic rotation
  - Dependency and container vulnerability scanning in CI/CD

## Long Term (9-18 months)

- High availability and multi-region architecture
- Formal SLO/SLI program with error budgets
- Extended enterprise controls (multi-tenant and policy enforcement)

## Milestones

- M1: Stable microservices production operations with validated runbooks
- M2: Advanced admin controls + full observability baseline
- M3: Scale/HA and enterprise security posture improvements
