#!/bin/bash
# Setup script for local mail server (Dovecot + Postfix)
# Run with: sudo ./setup.sh

set -e

echo "=== Installing Dovecot (IMAP) + Postfix (SMTP) ==="

# Install packages non-interactively
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y dovecot-imapd postfix mailutils

# Configure Postfix for local-only mail
postconf -e "inet_interfaces = localhost"
postconf -e "mydestination = localhost, localhost.localdomain"
postconf -e "mynetworks = 127.0.0.0/8"

# Configure Dovecot to allow plaintext auth on localhost
cat > /etc/dovecot/conf.d/99-local.conf << 'EOF'
# Local testing configuration
disable_plaintext_auth = no
auth_mechanisms = plain login

# Listen only on localhost
listen = 127.0.0.1

# Mail location
mail_location = maildir:~/Maildir
EOF

# Restart services
systemctl restart postfix
systemctl restart dovecot

echo ""
echo "=== Installing Roundcube Webmail ==="

# Install Roundcube and dependencies
apt-get install -y roundcube roundcube-core roundcube-mysql apache2 php libapache2-mod-php

# Configure Apache to serve Roundcube
ln -sf /etc/roundcube/apache.conf /etc/apache2/conf-available/roundcube.conf
a2enconf roundcube

# Configure Roundcube for local IMAP
cat > /etc/roundcube/config.inc.php.local << 'EOF'
<?php
$config['default_host'] = 'localhost';
$config['default_port'] = 143;
$config['imap_auth_type'] = 'LOGIN';
$config['smtp_server'] = 'localhost';
$config['smtp_port'] = 25;
$config['smtp_user'] = '';
$config['smtp_pass'] = '';
EOF

# Restart Apache
systemctl restart apache2

echo ""
echo "=== Mail Server Ready ==="
echo ""
echo "Services:"
echo "  IMAP: localhost:143 (no SSL)"
echo "  SMTP: localhost:25 (no TLS)"  
echo "  Webmail: http://localhost/roundcube"
echo ""
echo "Create a test user:"
echo "  sudo adduser testmail"
echo ""
echo "Then update your .env:"
echo "  IMAP_HOST=localhost"
echo "  IMAP_PORT=143"
echo "  IMAP_USE_SSL=false"
echo "  SMTP_HOST=localhost"
echo "  SMTP_PORT=25"
echo "  SMTP_USE_TLS=false"
echo "  EMAIL_ADDRESS=testmail"
echo "  EMAIL_PASSWORD=<user password>"
