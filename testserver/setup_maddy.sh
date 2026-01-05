#!/bin/bash
# Setup script for Maddy Mail Server (production-ready)
# This creates a proper mail server accessible from Thunderbird/iPhone

set -e

DOMAIN="mail.local"
IP=$(hostname -I | awk '{print $1}')

echo "=== Setting up Maddy Mail Server ==="
echo "Domain: $DOMAIN"
echo "IP: $IP"
echo ""

# Create directories
mkdir -p /etc/maddy/certs
mkdir -p /var/lib/maddy
mkdir -p /run/maddy

# Generate self-signed SSL certificate
echo "=== Generating SSL Certificate ==="
openssl req -x509 -newkey rsa:4096 -sha256 -days 365 -nodes \
    -keyout /etc/maddy/certs/privkey.pem \
    -out /etc/maddy/certs/fullchain.pem \
    -subj "/CN=$DOMAIN" \
    -addext "subjectAltName=DNS:$DOMAIN,DNS:localhost,IP:$IP,IP:127.0.0.1"

# Copy config
cp "$(dirname "$0")/maddy.conf" /etc/maddy/maddy.conf

# Set permissions
chown -R maddy:maddy /var/lib/maddy
chown -R maddy:maddy /run/maddy
chmod 600 /etc/maddy/certs/privkey.pem

# Create systemd service
cat > /etc/systemd/system/maddy.service << 'EOF'
[Unit]
Description=Maddy Mail Server
After=network.target

[Service]
Type=simple
User=maddy
Group=maddy
ExecStart=/usr/local/bin/maddy -config /etc/maddy/maddy.conf
Restart=on-failure
RuntimeDirectory=maddy
StateDirectory=maddy

# Allow binding to privileged ports
AmbientCapabilities=CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
EOF

# Reload and start
systemctl daemon-reload
systemctl enable maddy
systemctl start maddy

echo ""
echo "=== Maddy Mail Server Started ==="
echo ""
echo "Now create a user:"
echo "  sudo maddy creds create user@$DOMAIN"
echo "  sudo maddy imap-acct create user@$DOMAIN"
echo ""
echo "Client Settings (Thunderbird/iPhone):"
echo "  Server: $IP (or $DOMAIN if you add to /etc/hosts)"
echo "  IMAP: Port 993 (SSL/TLS) or 143 (STARTTLS)"
echo "  SMTP: Port 587 (STARTTLS)"
echo "  Username: user@$DOMAIN"
echo ""
echo "Add to your devices' /etc/hosts or DNS:"
echo "  $IP    $DOMAIN"
