#!/bin/bash
set -e

APP_DIR=/opt/p2p-system

echo "[deploy] git pull origin main..."
sudo -u p2p git -C "$APP_DIR" pull origin main

echo "[deploy] Checking requirements changes..."
CHANGED=$(git -C "$APP_DIR" diff ORIG_HEAD HEAD --name-only 2>/dev/null | grep -E 'requirements' || true)
if [ -n "$CHANGED" ]; then
    echo "[deploy] Requirements changed — installing dependencies..."
    sudo -u p2p "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements_lock.txt" -q
    echo "[deploy] Dependencies updated."
else
    echo "[deploy] Dependencies unchanged, skipping pip."
fi

echo "[deploy] Restarting services..."
systemctl restart p2p-tracker p2p-api
sleep 2

echo "[deploy] Status:"
systemctl status p2p-tracker --no-pager | head -5
systemctl status p2p-api --no-pager | head -5

echo "[deploy] Done."
