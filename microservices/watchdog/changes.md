# changes.md — watchdog

## 1.0.3 (2026-07-01)

### Changed
- **Health endpoint version reporting**: `/health` now returns `version` (from `app.version`)
  and `started_at` (module-load timestamp) for display in the admin panel version table.

## 1.0.2 (2026-07-01)

### Changed
- **`DEFAULT_SERVICE_URLS` completeness**: Added `support_hub` (http://127.0.0.1:8008)
  and `workforce_ops` (http://127.0.0.1:8009) so the watchdog now monitors all 8
  microservices instead of only 6.
- Version bumped from 1.0.0 to 1.0.2.
