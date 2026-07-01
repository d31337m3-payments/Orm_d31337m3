# changes.md — shared

## 1.0.1 (2026-07-01)

### Changed
- **Retry-backoff for Infisical initialization**: `init_infisical()` and `load_service_secrets()`
  now wrap their Infisical API calls in `_with_retry_backoff()` with exponential backoff
  (base 1s, multiplier 2x, max 30s, jitter 10%) and up to 5 retries.
- **Infisical health tracking**: Added module-level globals (`_infisical_connected`,
  `_infisical_last_success`, `_infisical_last_failure`, `_infisical_error`,
  `_infisical_latency_ms`, `_infisical_retry_count`) and `get_infisical_status()`
  function for integration into the system health pipeline.
