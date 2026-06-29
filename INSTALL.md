# Installation and Deployment

This repository runs on a React frontend plus an API microservices stack.

## Prerequisites

- Linux host with `systemd`
- Python 3.11+
- Node.js 18+
- Nginx installed

## 1) Clone and install dependencies

```bash
git clone https://github.com/d31337m3-payments/Orm_d31337m3.git
cd Orm_d31337m3

cd frontend
npm install
cd ..

cd microservices
./install_deps.sh
cd ..
```

## 2) Configure Nginx

```bash
sudo ./setup-nginx.sh
```

This enables the repo nginx site and routes `/api/*` to `orchestrator` (`127.0.0.1:8006`).

## 3) Install microservices as boot-persistent systemd units

```bash
cd microservices
./systemd/install_systemd_services.sh
```

## 4) Validate deployment gate

```bash
cd microservices
./gate_check.sh
```

## 5) Rollback (if needed)

```bash
cd microservices
./rollback.sh
```

## Service Ports

- `client_index` -> `8002`
- `payments` -> `8003`
- `data_handling` -> `8004`
- `auditor` -> `8005`
- `orchestrator` -> `8006`
- `watchdog` -> `8007`

## Operational Commands

Check all unit states:

```bash
for s in auditor client-index data-handling payments watchdog orchestrator; do
  unit="d31337m3-${s}.service"
  printf '%s enabled=%s active=%s\n' "$unit" "$(systemctl is-enabled "$unit")" "$(systemctl is-active "$unit")"
done
```

Inspect Nginx:

```bash
sudo nginx -t
sudo nginx -T
```
