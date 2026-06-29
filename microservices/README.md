# Microservices Operations

This directory contains the API microservices and production-oriented startup scripts.

## Services and Ports

- `client_index` -> `8002`
- `payments` -> `8003`
- `data_handling` -> `8004`
- `auditor` -> `8005`
- `orchestrator` -> `8006`
- `watchdog` -> `8007`
- `support_hub` -> `8008`
- `workforce_ops` -> `8009`

## One-time Setup

```bash
cd microservices
./install_deps.sh
```

## Start / Stop

```bash
cd microservices
./start_all.sh
./health_check.sh
```

```bash
cd microservices
./stop_all.sh
```

## Systemd (Production)

Install and enable all microservices as boot-persistent systemd units:

```bash
cd microservices
chmod +x systemd/install_systemd_services.sh systemd/uninstall_systemd_services.sh
./systemd/install_systemd_services.sh
```

Remove systemd units:

```bash
cd microservices
./systemd/uninstall_systemd_services.sh
```

## Gate and Rollback

Run go-live gate checks:

```bash
cd microservices
chmod +x gate_check.sh
./gate_check.sh
```

Run rollback command pack:

```bash
cd microservices
chmod +x rollback.sh
./rollback.sh
```

## Nginx API Routing

The repository Nginx config routes `/api/*` to orchestrator on port `8006`:

- File: `nginx-d31337m3.conf`
- Upstream: `http://127.0.0.1:8006/api/`

Apply nginx config on host:

```bash
sudo ./setup-nginx.sh
```

## Runbook Alignment

This setup follows the startup order in:

- `docs/agent_go_live_microservices.md`
- `docs/go_live_quick_runbook.md`

## Notes

- Logs are written to `microservices/logs/*.log`.
- PIDs are written to `microservices/pids/*.pid`.
- Secrets are loaded Infisical-first via `shared/secrets_manager.py`, with environment variables as fallback.
- Set `INFISICAL_PROJECT_ID`, `INFISICAL_ENVIRONMENT`, and either `INFISICAL_SERVICE_TOKEN` or `INFISICAL_CLIENT_ID` + `INFISICAL_CLIENT_SECRET` on each service.
- Local persistence defaults (override via env/Infisical keys):
	- Orchestrator support DB: `ORCHESTRATOR_SUPPORT_DB_PATH` (default `/tmp/d31337m3_orchestrator_support.db`)
	- Payments DB: `PAYMENTS_DB_PATH` (default `/tmp/d31337m3_payments.db`)
	- Data handling DB: `DATA_HANDLING_DB_PATH` (default `/tmp/d31337m3_data_handling.db`)
	- Watchdog DB: `WATCHDOG_DB_PATH` (default `/tmp/d31337m3_watchdog.db`)
	- Auditor DB: `AUDITOR_DB_PATH` (default `/tmp/d31337m3_auditor.db`)
- Watchdog live probing can be configured with:
	- `WATCHDOG_SERVICE_URLS` as JSON map, for example `{"client_index":"http://127.0.0.1:8002"}`
	- `WATCHDOG_HEALTH_TIMEOUT_SECONDS` probe timeout
	- `WATCHDOG_HEALTH_WINDOW_MINUTES` alert evaluation window
	- `WATCHDOG_ALERT_DESTINATION` notification sink label
