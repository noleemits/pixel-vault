#!/usr/bin/env bash
# PixelVault API — Hetzner VPS Setup Script
# Run as root on a fresh Ubuntu 24.04 server.
set -euo pipefail

DOMAIN="vaultapi.noleemits.com"
APP_DIR="/opt/pixelvault"
APP_USER="pixelvault"
REPO="https://github.com/noleemits/pixel-vault.git"

echo "=== 1/7  System update ==="
apt-get update && apt-get upgrade -y
apt-get install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx git ufw

echo "=== 2/7  Firewall ==="
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

echo "=== 3/7  Create app user ==="
if ! id "$APP_USER" &>/dev/null; then
    useradd --system --shell /usr/sbin/nologin --home-dir "$APP_DIR" "$APP_USER"
fi

echo "=== 4/7  Clone repo & install deps ==="
if [ -d "$APP_DIR/.git" ]; then
    echo "Repo already cloned, pulling latest..."
    cd "$APP_DIR" && git pull
else
    git clone "$REPO" "$APP_DIR"
fi

cd "$APP_DIR"
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt

mkdir -p storage/images
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

echo "=== 5/7  Systemd service ==="
cp deploy/pixelvault.service /etc/systemd/system/pixelvault.service
systemctl daemon-reload
systemctl enable pixelvault

echo "=== 6/7  Nginx config ==="
cp deploy/nginx-pixelvault.conf /etc/nginx/sites-available/pixelvault
ln -sf /etc/nginx/sites-available/pixelvault /etc/nginx/sites-enabled/pixelvault
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo "=== 7/7  SSL certificate ==="
mkdir -p /var/www/certbot
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email stevenoleemits@gmail.com

systemctl restart nginx

echo ""
echo "============================================"
echo "  Setup complete!"
echo "  Next steps:"
echo "    1. Create /opt/pixelvault/.env (see .env.example)"
echo "    2. Run: alembic upgrade head"
echo "    3. Run: systemctl start pixelvault"
echo "    4. Test: curl https://${DOMAIN}/health"
echo "============================================"
