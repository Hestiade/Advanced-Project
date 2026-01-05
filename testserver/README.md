# Test Mail Server Setup

Local mail server using Dovecot (IMAP) + Postfix (SMTP) installed via apt.

## Quick Setup

```bash
# Install and configure (requires sudo)
sudo ./setup.sh

# Create a test user
sudo adduser testmail
# Enter a password when prompted

# Send a test email
./send_test_email.sh testmail "Hello" "This is a test"
```

## Configuration

After setup, update your `.env`:

```bash
IMAP_HOST=localhost
IMAP_PORT=143
IMAP_USE_SSL=false
SMTP_HOST=localhost
SMTP_PORT=25
SMTP_USE_TLS=false
EMAIL_ADDRESS=testmail
EMAIL_PASSWORD=<the password you set>
```

## Ports

| Service | Port/URL | Notes |
|---------|----------|-------|
| IMAP | localhost:143 | No SSL (local only) |
| SMTP | localhost:25 | No TLS (local only) |
| **Webmail** | http://localhost/roundcube | Roundcube admin panel |

## Troubleshooting

```bash
# Check service status
sudo systemctl status dovecot
sudo systemctl status postfix

# View mail logs
sudo tail -f /var/log/mail.log

# Check user's mailbox
ls ~/Maildir/new/
```

## Uninstall

```bash
sudo apt remove dovecot-imapd postfix mailutils
sudo apt autoremove
```
