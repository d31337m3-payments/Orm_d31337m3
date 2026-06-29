# PM2 Setup (Legacy)

This file is kept only for historical context.

## Current Status

PM2 is no longer the primary production process manager for API services.
Production services run as `systemd` units under `microservices/systemd/*.service`.

## Use Instead

Use the microservices operations docs:

- `microservices/README.md`
- `docs/agent_go_live_microservices.md`
- `docs/go_live_quick_runbook.md`

## If You Still Need PM2 (Development Only)

PM2 can still be used manually for ad-hoc development experiments, but it is not part of the supported production deployment path.
