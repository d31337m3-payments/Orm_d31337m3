# Orm_d31337m3

A full-stack MicroSaaS Automated Online Privacy and Reputation Management platform with a FastAPI backend and a React frontend. This repository contains the backend API, frontend UI, and deployment helpers (Nginx configuration and setup script).

## Overview

- Backend: FastAPI (Python) located in the `backend/` directory.
- Frontend: React (CRA-like) located in the `frontend/` directory.
- Nginx: `nginx-d31337m3.conf` and `setup-nginx.sh` provide a reverse-proxy configuration.

## Quick Start (Development)

Prerequisites:
- Python 3.11+
- Node.js 18+
- npm or yarn
- nginx (for proxying; optional in local dev)

Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --host 127.0.0.1 --port 8001 --reload
```

Frontend

```bash
cd frontend
npm install
npm start
# or: yarn
# Frontend dev server listens on port 3000 by default
```

## Production / Deployment (NGINX)

 `setup-nginx.sh` to install a site into `/etc/nginx/sites-available` and enable it.

Run as root on the target host:

```bash
sudo ./setup-nginx.sh
```

This does the following:
- Removes the Debian default site from `/etc/nginx/sites-enabled`
- Creates a symlink in `/etc/nginx/sites-enabled` and reloads nginx

Ensure your frontend server (or static build) is available on `127.0.0.1:3000` and backend on `127.0.0.1:8001`, or update the `proxy_pass` targets accordingly in `nginx-d31337m3.conf`.

## Running Tests

Python/Backend tests are located under `backend/tests` and repository-level tests under `tests/`.

Run tests with pytest:

```bash
cd backend
source venv/bin/activate
pytest -q
```

## Troubleshooting

- If the Nginx welcome page appears for your domain, ensure the default site is disabled:

```bash
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl reload nginx
```

- If the browser shows a blank page but `curl` returns app HTML, check the browser console for JS/CSS asset errors and ensure the frontend static assets are being served at `/static/`.

- To inspect the active Nginx configuration:

```bash
sudo nginx -T
```

## Contributing

Open an issue or submit a PR. Follow the existing code style and add tests for new features.

## License

The Open-Source portions of thks project are licenced under the MIT License. See [LICENSE](LICENSE) for details. The project may include third-party dependencies with their own licenses; please review those as needed. There may be proprietary components or services integrated into the project; consult the documentation for any usage restrictions. Proprietary components are not covered by the MIT License and may have separate licensing terms, as well as potential fees or usage restrictions. Users should review the documentation and licensing information for any proprietary components before use. D31337m3.com is a trademark of the project owner and may not be used without permission. The project owner reserves all rights to the trademark and any associated branding or logos. (C) 2024 D31337m3.com. All rights reserved.

## Documentation
Additional project documentation is available in the `docs/` folder. Key documents:

- [Docs index](docs/README.md)
- [Security & Privacy](docs/security_and_privacy.md)
- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Future Development](docs/future_development.md)

For contribution guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).
