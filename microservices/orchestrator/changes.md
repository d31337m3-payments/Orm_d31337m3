# changes.md — orchestrator

## 1.0.5 (2026-07-01)

### Added
- **Employee-level access to workforce/support endpoints**: Added `verify_employee_or_admin`
  dependency that accepts service tokens, admin tokens, and user tokens with an
  `employee_number` claim. Updated all 15 workforce and 6 support admin endpoints from
  `verify_admin_or_service` to the broader dependency so employees can access these portals.

### Changed
- **Impersonation token includes `employee_number`**: `admin_impersonate()` now passes
  `employee_number=user.get("employee_number")` to `create_user_token()`.

## 1.0.4 (2026-07-01)

### Added
- **Public health-summary endpoint**: Added `/api/public/health-summary` (no auth) that
  returns all 8 microservices' status, version, and started_at for the landing page widget.
- **Public changelogs endpoint**: Added `/api/public/changelogs` (no auth) that aggregates
  all microservice `changes.md` files for the public security portal.
- **Infisical health check**: Added Infisical connection status to `GET /api/admin/health`
  and `GET /api/public/health-summary` via `get_infisical_status()` from shared module.

### Fixed
- **SMTP test and email always mocking**: `_send_email_sync()` and
  `POST /admin/health/smtp-test` both checked `_env_bool("SMTP_ENABLED", False)`,
  which always resolved to `False` (no such Infisical secret). Replaced with actual
  config presence check (`SMTP_HOST && SMTP_USERNAME && SMTP_PASSWORD && SMTP_FROM`).
  Removed `_env_bool("SMTP_ENABLED")` references from admin settings endpoint too.
  All `SMTP_ENABLED` references purged from both orchestrator and client_index.

### Changed
- **Version tracking in service registry**: `_probe_service_status()` now returns a dict with
  `version` and `started_at` parsed from each service's `/health` response. The registry
  tracks `last_version` so version changes (e.g. after an update) are visible.
- **Startup sequence API updated**: `/api/health/startup-sequence` now includes `version`,
  `last_version`, and `started_at` per service for the admin panel version table.

## 1.0.3 (2026-07-01)

### Fixed
- **SMTP health check falsely reporting "not set"**: SMTP status was gated on
  `_env_bool("SMTP_ENABLED", False)` rather than actual config presence. Changed to check
  `SMTP_HOST` and `SMTP_USERNAME` directly from Infisical, matching the PayPal check pattern.
  Status shows "ok" when both values exist in Infisical regardless of an `SMTP_ENABLED` flag.
- **`_secret()` reverted to Infisical-only**: Removed `os.environ` fallback that was added
  incorrectly — secrets must come from Infisical only.

## 1.0.2 (2026-07-01)

### Changed
- **`SERVICE_STARTUP_ORDER` parity**: Updated `main.py` to include `support_hub` and
  `workforce_ops`, matching the existing `routes.py` definition. The list grows from 6 to 8
  services: `auditor`, `client_index`, `data_handling`, `payments`, `support_hub`,
  `workforce_ops`, `watchdog`, `orchestrator`.
- Version bumped from 1.0.0 to 1.0.2 (parity update).
