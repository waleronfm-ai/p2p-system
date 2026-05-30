# Deploy — P2P System

Systemd unit files for Ubuntu 24.04 VPS.

## Assumptions

| Parameter | Value |
|---|---|
| Deploy path | `/opt/p2p-system` |
| System user | `p2p` (non-root) |
| Python venv | `/opt/p2p-system/venv` |
| Config | `/opt/p2p-system/config/.env` (read by pydantic-settings automatically) |
| API port | `8000` |

## Setup

### 1. Create user and clone repo

```bash
sudo useradd -r -s /bin/bash -m p2p
sudo mkdir -p /opt/p2p-system
sudo git clone https://github.com/YOUR/p2p-system.git /opt/p2p-system
sudo chown -R p2p:p2p /opt/p2p-system
```

### 2. Create venv and install dependencies

```bash
sudo -u p2p bash -c "cd /opt/p2p-system && python3 -m venv venv && venv/bin/pip install -r requirements.txt"
```

### 3. Create config/.env

```bash
sudo -u p2p cp /opt/p2p-system/config/.env.example /opt/p2p-system/config/.env
sudo -u p2p nano /opt/p2p-system/config/.env
```

Fill in `API_KEY` (generate: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`)
and set `CORS_ORIGINS` to the URL(s) your frontend will be served from.

### 4. Initialize database

```bash
sudo -u p2p bash -c "cd /opt/p2p-system && PYTHONPATH=/opt/p2p-system venv/bin/python -m scripts.init_db"
```

### 5. Install and enable services

```bash
sudo cp /opt/p2p-system/deploy/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now p2p-tracker p2p-api
```

### 6. Verify

```bash
sudo systemctl status p2p-tracker p2p-api
journalctl -u p2p-tracker -f
journalctl -u p2p-api -f
```

### Updating

```bash
cd /opt/p2p-system
sudo -u p2p git pull
sudo systemctl restart p2p-tracker p2p-api
```

---

## Security

API listens on `0.0.0.0` for direct frontend access from local machine.

Protection layers:
- ufw allows only ports 22 (SSH) and 8000 (API)
- `API_KEY` required for write endpoints (POST/DELETE)
- CORS restricts browser-based requests to whitelisted origins

To improve security later: install Cloudflare Tunnel and switch ExecStart
to `--host 127.0.0.1` (commented variant available in `deploy/systemd/p2p-api.service`).

```bash
# ufw setup
sudo ufw allow 22/tcp
sudo ufw allow 8000/tcp
sudo ufw enable
```
