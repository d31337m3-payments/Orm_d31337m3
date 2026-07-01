# changes.md — client_index

## 1.0.4 (2026-07-01)

### Fixed
- **SMTP emails always mocked**: `_send_email_sync()` and `_is_smtp_enabled()` both
  gated on `get_bool_secret("SMTP_ENABLED", False)` which resolved to `False` when no
  such Infisical secret exists. Replaced with actual config presence checks
  (`SMTP_HOST && SMTP_USERNAME && SMTP_PASSWORD`). Emails now send when SMTP is
  configured regardless of a separate flag.

## 1.0.3 (2026-07-01)

### Changed
- **Health endpoint version reporting**: `/health` now returns `version` (from `app.version`)
  and `started_at` (module-load timestamp) for display in the admin panel version table.

## 1.0.2 (2026-07-01)

### Changed
- Version bumped from 1.0.0 to 1.0.2 (parity update across all microservices).
