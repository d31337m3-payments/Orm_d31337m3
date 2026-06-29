# Android Admin App + Ops Services Plan

## Objective
Build a mobile-only Android app for internal staff to administer the platform, and expand platform capabilities with:
- Customer live support chat + trouble tickets
- Employee scheduling + payroll operations
- Host-level admin controls from the Admin Operations panel

## What Is Implemented Now

### Admin host controls
The orchestrator now exposes secured operations endpoints:
- `GET /api/admin/ops/capabilities`
- `POST /api/admin/ops/restart-service/{service_name}`
- `POST /api/admin/ops/restart-all`
- `POST /api/admin/ops/reboot-server`

These are disabled by default and require:
- `ADMIN_ENABLE_HOST_CONTROLS=true`
- systemd/sudo permissions for the orchestrator process user

Reboot endpoint requires a confirmation token in payload:
- `{ "confirm": "REBOOT_PHYSICAL_SERVER" }`

### New microservice scaffolds
Two new services were added:
- `microservices/support_hub` (port `8008`)
- `microservices/workforce_ops` (port `8009`)

Both include health endpoints and authenticated API scaffolds for staff/service tokens.

### Frontend operations controls
`Admin Operations` now includes:
- Restart single service buttons
- Restart all services button
- Reboot physical server button
- Capability indicator (enabled/disabled)

## New Service API Surface (Scaffold)

### Support Hub (`/api/support`)
- `GET /chats`
- `POST /chats`
- `GET /chats/{chat_id}/messages`
- `POST /chats/{chat_id}/messages`
- `GET /tickets`
- `POST /tickets`
- `PATCH /tickets/{ticket_id}`

### Workforce Ops (`/api/workforce`)
- `GET /shifts`
- `POST /shifts`
- `PATCH /shifts/{shift_id}`
- `GET /timesheets`
- `POST /timesheets`
- `GET /payroll-runs`
- `POST /payroll-runs`

Note: current scaffold stores data in memory. Persist to DB in Phase 2.

## Android-Only Admin App Blueprint

## Recommended stack
- Language: Kotlin
- UI: Jetpack Compose (Material 3)
- Architecture: Clean Architecture + MVVM
- Networking: Retrofit + OkHttp + Moshi/Kotlinx Serialization
- Auth storage: EncryptedSharedPreferences
- Push alerts: Firebase Cloud Messaging
- Offline queue: Room + WorkManager
- CI: GitHub Actions + Gradle + Android Lint + unit/UI tests

## App modules
- `app`: navigation shell, dependency graph
- `core-network`: Retrofit clients + interceptors
- `core-auth`: login/session/token refresh
- `feature-ops`: service restart/reboot controls
- `feature-support`: live chat and tickets
- `feature-workforce`: scheduling, timesheets, payroll run approvals
- `core-ui`: reusable components/theme

## Mobile screens
- Login (staff/admin only)
- Service Health Dashboard
- Service Control (restart single/all)
- Host Control (reboot with 2-step confirm)
- Live Chat Inbox + Session Detail
- Ticket Queue + SLA/Priority views
- Shift Calendar and Assignment Board
- Payroll Run Approvals and Export Actions
- Audit Timeline

## Security requirements
- Require admin role claims in JWT for host controls
- Add device binding and short session TTL for staff accounts
- Enforce MFA for reboot endpoint and payroll approvals
- Use signed audit events for all sensitive actions
- Redact secrets from mobile responses

## Recommended production data model additions
- `support_chat_sessions`
- `support_chat_messages`
- `support_tickets`
- `employee_profiles`
- `employee_shifts`
- `employee_timesheets`
- `payroll_runs`
- `payroll_line_items`
- `ops_audit_events`

## Suggested rollout phases

### Phase 1: foundation (done/started)
- Admin ops endpoints + UI controls
- Support/workforce microservice scaffolds
- Basic route coverage and token auth

### Phase 2: persistence + integrations
- Replace in-memory stores with PostgreSQL tables
- Add websocket or SSE only for support chat realtime
- Integrate payroll provider/export pipeline
- Add ticket SLA policies and assignment engine

### Phase 3: Android app MVP
- Staff auth + role-gated navigation
- Health/operations controls
- Ticket queue and basic chat agent UI
- Shift management + payroll run review

### Phase 4: hardening
- Device attestation, MDM policy, biometric unlock
- Full observability dashboards and alerting
- Disaster recovery runbooks in-app and on-call playbooks

## Deployment checklist
- Add service unit files for:
  - `d31337m3-support-hub`
  - `d31337m3-workforce-ops`
- Update nginx upstream routes if exposing direct paths
- Add secrets:
  - `ADMIN_ENABLE_HOST_CONTROLS`
  - support/workforce DB connection and SMTP settings
- Restrict host-control endpoints by IP and role
- Add integration tests for restart/reboot protections

## Example Android API contracts

### Restart single service
Request:
```http
POST /api/admin/ops/restart-service/client_index
Authorization: Bearer <staff-admin-token>
```

Response:
```json
{
  "ok": true,
  "service": "client_index",
  "unit": "d31337m3-client-index"
}
```

### Create ticket
Request:
```http
POST /api/support/tickets
Authorization: Bearer <staff-token>
Content-Type: application/json

{
  "customer_id": "cust_123",
  "title": "Cannot verify payment",
  "description": "Customer submitted tx hash but status not updating",
  "priority": "high"
}
```

Response:
```json
{
  "ok": true,
  "ticket": {
    "id": "...",
    "status": "open"
  }
}
```

### Create payroll run
Request:
```http
POST /api/workforce/payroll-runs
Authorization: Bearer <staff-admin-token>
Content-Type: application/json

{
  "period_start": "2026-07-01",
  "period_end": "2026-07-15",
  "total_gross": 42000,
  "total_net": 33400,
  "line_items": []
}
```

Response:
```json
{
  "ok": true,
  "payroll_run": {
    "id": "...",
    "status": "draft"
  }
}
```
