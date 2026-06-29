# Orm_d31337m3

Full-stack privacy and reputation management platform with:

- React frontend (`frontend/`)
- API microservices stack (`microservices/`)
- Nginx edge routing (`nginx-d31337m3.conf` + `setup-nginx.sh`)

## Current Implementation

API services are organized as microservices:

- `client_index` (`8002`)
- `payments` (`8003`)
- `data_handling` (`8004`)
- `auditor` (`8005`)
- `orchestrator` (`8006`)
- `watchdog` (`8007`)

Nginx routes `/api/*` to `orchestrator` on `127.0.0.1:8006`.

## Local Development

### Frontend

```bash
cd frontend
npm install
npm start
```

### Microservices

```bash
cd microservices
./install_deps.sh
./start_all.sh
./health_check.sh
```

Stop microservices:

```bash
cd microservices
./stop_all.sh
```

## Production Operations

Install and enable systemd services:

```bash
cd microservices
./systemd/install_systemd_services.sh
```

Run the deployment gate:

```bash
cd microservices
./gate_check.sh
```

Rollback command pack:

```bash
cd microservices
./rollback.sh
```

## Nginx

Apply repository nginx config:

```bash
sudo ./setup-nginx.sh
```

Inspect active nginx config:

```bash
sudo nginx -T
```

## Documentation

- [Documentation Index](docs/README.md)
- [Agent Go-Live Guide](docs/agent_go_live_microservices.md)
- [Go-Live Quick Runbook](docs/go_live_quick_runbook.md)
- [Security and Privacy](docs/security_and_privacy.md)
- [Roadmap](docs/roadmap.md)
- [Future Development](docs/future_development.md)
- [Microservices Operations](microservices/README.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
