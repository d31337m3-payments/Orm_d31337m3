# Microservices Refactor Plan

This document defines a detailed microservice refactor plan for the backend. It is written as a guide for an agent or engineer to split the existing backend into separate services while preserving a coordinated orchestration model.

## Goals

- Separate major responsibilities into dedicated services.
- Preserve strong security boundaries and auditability.
- Support service discovery, startup ordering, and network-level controls.
- Provide a simple orchestration layer that acts as the ring leader.

## Target Services

### 1. `payments`
- Handles all payment flows and subscription lifecycle events.
- Manages activation of paid plans when users upgrade from trial.
- Coordinates with `client_index` for user billing state and entitlements.
- Integrates with payment providers, webhooks, and retry logic.

Responsibilities:
- Process payment requests and callbacks.
- Validate pricing plans and trial conversion.
- Record transactions to the audit log via `auditor`.
- Emit events for plan upgrades and entitlement changes.

### 2. `data_handling`
- Responsible for database interactions, scraping, indexing, and data pipelines.
- Controls ingestion of external data, transformation, and search indexing.
- Provides a data API for downstream services to query processed content.

Responsibilities:
- Maintain the application database schema and migrations.
- Run scraping workflows and data enrichment.
- Build/refresh indexes for search and retrieval.
- Provide a service-level API for data queries and persistence.
_ ** Ensuring that all data writes are logged to the `auditor` service for compliance and traceability. Security of this data is also paramount. 
It must ensure that sensitive data is encrypted at rest and in transit, and that access controls are strictly enforced. Employee access to this service should be limited and monitored, with audit trails for all administrative actions. And client data should not accessable to other services, or if it is, it should be done through secure APIs with proper authentication and authorization checks.

### 3. `client_index`
- The user database service with secure storage and credential handling.
- Manages authentication, account creation, password storage, roles, and sessions.
- Acts as the authoritative source for user identity and profile metadata.

Responsibilities:
- Authenticate logins and issue tokens/sessions.
- Store credentials securely using password hashing and secrets management.
- Provide authorization metadata for other services.
- Handle user lifecycle events (registration, password reset, profile updates).

### 4. `auditor`
- Records all critical actions for auditing, compliance, and investigation.
- Stores immutable audit trails for service events, user actions, and administrative changes.
- Exposes audit query APIs for internal compliance tooling.

Responsibilities:
- Accept event writes from all services.
- Persist audit records with timestamps, actor, action type, and metadata.
- Provide search/filter endpoints for audit analysis.
- Enforce tamper-resistant storage and write-only append semantics.

### 5. `watchdog`
- Observes service health and operational state.
- Detects failure conditions and triggers recovery or alerting.
- Coordinates with the orchestrator for restart or failover.

Responsibilities:
- Poll health endpoints for each service.
- Evaluate latency, error rates, and heartbeat signals.
- Alert operators and escalate issues when services degrade.
- Optionally trigger automated restarts through the orchestrator.

### 6. `orchestrator`
- The ring leader that coordinates service startup, dependencies, and network access.
- Manages service registration, configuration, and lifecycle events.
- Provides central routing for internal API calls and service discovery.

Responsibilities:
- Start services in the correct dependency order.
- Provide environment configuration to services.
- Track service availability and orchestration state.
- Support graceful shutdown and rolling updates.

## Architecture Overview

The overall flow should look like:

- `client_index` is the identity provider and login gateway.
- `payments` handles billing, subscription transitions, and plan activations.
- `data_handling` owns persistent data models and indexing.
- `auditor` logs all audited actions.
- `watchdog` monitors all services and reports health.
- `orchestrator` sequences startup and manages service metadata.

### Interaction Patterns

- Use REST or gRPC APIs for service-to-service communication.
- Prefer event-driven patterns for lifecycle events and audit writes.
- Avoid direct database access across service boundaries.
- Enforce authenticated API calls with mutual TLS or service tokens.

## Step-by-step Refactor Guide

### Step 1: Define service boundaries and APIs
- Document the exact responsibilities of each microservice.
- Design API contracts for each service.
- Create OpenAPI specs or protobuf schemas for service APIs.

### Step 2: Establish security boundaries
- Isolate credentials and secrets per service.
- Use secure credential storage for `client_index` and `payments`.
- Add service-to-service auth using tokens, signed JWTs, or mTLS.
- Ensure audit writes to `auditor` are authenticated and append-only.

### Step 3: Split the existing backend repository
- Create separate service packages or directories for each microservice.
- Extract shared libraries into common packages (e.g. `shared/db`, `shared/logging`).
- Retain the current backend as a coordination layer during refactor.

### Step 4: Build `client_index`
- Implement authentication, user registration, password hashing, and session/token issuance.
- Add secure credential storage using a suitable secret storage mechanism.
- Provide role and permission metadata.
- Add endpoints for user and session management.

### Step 5: Build `payments`
- Integrate payment provider operations.
- Implement plan upgrade flows, trial conversion, and entitlement activation.
- Add webhook handling and error/retry logic.
- Emit audit events for financial actions.

### Step 6: Build `data_handling`
- Migrate database models into a dedicated data service.
- Separate scraping and indexing jobs from request handling.
- Provide a data query API for other services.
- Implement migrations and data persistence logic.

### Step 7: Build `auditor`
- Create a write-only endpoint for audit events.
- Store events immutably and add query support.
- Make sure every service sends audit records for business-critical actions.

### Step 8: Build `watchdog`
- Implement health checks for each service.
- Add monitoring for status, response times, and failures.
- Optionally integrate with alerting or the orchestrator.

### Step 9: Build the `orchestrator`
- Define startup order based on dependencies.
- Manage config distribution and service registration.
- Provide a simple UI or status API for active service state.
- Implement graceful restart/shutdown.

### Step 10: Migrate and validate
- Migrate backend functionality incrementally from the monolith.
- Run end-to-end tests for each refactor stage.
- Validate audit logs, payment workflows, and authentication.
- Use the watchdog to confirm service health after each deployment.

## Networking and Startup

### Service Registry and Discovery
- The orchestrator should provide a service registry.
- Services discover each other through a central service directory or DNS-based naming.
- Use consistent internal hostnames like `client_index`, `payments`, `data_handling`, `auditor`, `watchdog`.

### Network Segmentation
- Place microservices on a private network segment.
- Expose only the orchestrator or public gateway to external traffic.
- Restrict management access to the orchestration/control plane.

### Startup Order

1. `auditor` — available for event recording.
2. `client_index` — identity and auth ready.
3. `data_handling` — data store ready.
4. `payments` — billing flows ready.
5. `watchdog` — monitoring can begin.
6. `orchestrator` — coordinates the others and exposes global state.

### Service Startup
- Each service should expose a `/health` endpoint.
- The orchestrator should verify readiness before marking a service available.
- Support retries and backoff for failed startup attempts.

## Orchestrator / Ring Leader

The orchestrator should:
- Be the single source of truth for service state.
- Provide discovery metadata and startup status.
- Validate service dependencies and startup conditions.
- Optionally provide a simple API gateway for external clients.
- Coordinate the `watchdog` if automated restart is enabled.

### Orchestrator Responsibilities
- Start services in order.
- Collect logs and health statuses.
- Configure environment variables and secrets.
- Manage service lifecycle events (deploy, scale, restart, stop).

## Operational Concerns

### Logging and Tracing
- Use centralized structured logging across services.
- Correlate requests across service boundaries using trace IDs.
- Emit audit-related events from each service.

### Configuration
- Store service config in environment variables or a central config service.
- Keep secrets out of source control.
- Use the orchestrator to inject runtime configuration.

### Deployment
- Start with containerized services for portability.
- Use a process manager or Kubernetes-style deployment primitive if available.
- Ensure the orchestrator can restart failed services.

## Agent Instructions

When executing this refactor, an agent should:
1. Analyze the current backend architecture and identify module boundaries.
2. Extract core responsibilities into separate service packages.
3. Define APIs and events for service interaction.
4. Implement security controls for authentication, service tokens, and data access.
5. Build audit trails through the `auditor` service.
6. Use the orchestrator to manage service lifecycle and startup dependencies.
7. Validate each split with integration and end-to-end tests.

## Notes

- This refactor assumes the existing monolithic backend can be decomposed without changing the core domain model drastically.
- Keep shared utility code isolated and avoid coupling services by database access.
- Use the `auditor` service as the permanent source of truth for sensitive operations and compliance.
