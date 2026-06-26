# Deploying d31337m3

## One-click install (Ubuntu / Debian)

```bash
git clone https://github.com/YOUR-ORG/d31337m3.git
cd d31337m3
chmod +x install.sh
sudo ./install.sh
```

The installer will:
1. Install Python 3.11, Node 20 LTS, Yarn, MongoDB 7.0, and Supervisor
2. Prompt you for configuration (admin email/password, SMTP creds, wallet, etc.)
3. Generate a random `JWT_SECRET`
4. Write `backend/.env` and `frontend/.env`
5. Install backend + frontend dependencies
6. Register the services with supervisor and start them
7. Configure UFW firewall rules (run `sudo ufw enable` when ready)
8. Run a health check on both services

When finished, the dashboard is available at:
- **Frontend** → `http://YOUR_SERVER:3000`
- **Backend API** → `http://YOUR_SERVER:8001/api`

## Quick re-config

To change settings later, edit `backend/.env` or `frontend/.env` and restart:

```bash
sudo supervisorctl restart d31337m3-backend
sudo supervisorctl restart d31337m3-frontend
```

## Promo code configuration

The backend supports two promo slots using environment variables:

- `PROMO_CODE_PRIMARY`: primary promo code (default: `OCanada75`)
- `PROMO_PERCENT_PRIMARY`: primary promo discount percentage (default: `75`)
- `PROMO_EXPIRES_PRIMARY`: primary promo expiration date in `YYYY-MM-DD` format (default: `2026-12-31`)
- `PROMO_CODE_SECONDARY`: optional secondary promo code
- `PROMO_PERCENT_SECONDARY`: optional secondary promo percentage
- `PROMO_EXPIRES_SECONDARY`: optional secondary promo expiration date

After editing `backend/.env`, restart the backend service:

```bash
sudo supervisorctl restart d31337m3-backend
```

## Production hardening checklist

- [ ] Put Nginx in front of ports 3000 and 8001 with Let's Encrypt for HTTPS
- [ ] Disable `--reload` in `/etc/supervisor/conf.d/d31337m3-backend.conf`
- [ ] Run `cd frontend && yarn build` and serve `frontend/build/` with Nginx instead of `yarn start`
- [ ] Enable UFW: `sudo ufw enable`
- [ ] Set up MongoDB auth: `mongosh` → create user, then add `?authSource=admin` to `MONGO_URL`
- [ ] Add SPF / DKIM / DMARC records for d31337m3.com to maximize SMTP deliverability
- [ ] Schedule a daily Mongo backup: `mongodump --db d31337m3_db --out /var/backups/...`
