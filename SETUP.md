# AI Mail Redirection Agent - Setup Guide

Complete setup instructions for deploying the AI Mail Redirection Agent with a local Maddy mail server.

---

## Prerequisites

- **Linux** (Ubuntu/Debian)
- **Python 3.10+**
- **Thunderbird** (optional, for email client testing)

---

## 1. Python Environment Setup

```bash
# Create virtual environment (without pip, then bootstrap)
rm -rf .venv
python3 -m venv --without-pip .venv
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
.venv/bin/python3 get-pip.py
rm get-pip.py

# Install dependencies
.venv/bin/pip install -r requirements.txt
```

---

## 2. Maddy Mail Server Installation

### Download & Extract

```bash
# Download Maddy v0.8.1
wget https://github.com/foxcpp/maddy/releases/download/v0.8.1/maddy-0.8.1-x86_64-linux-musl.tar.zst

# Extract and move to mail_server/
tar -I zstd -xvf maddy-0.8.1-x86_64-linux-musl.tar.zst
mkdir -p mail_server
mv maddy-0.8.1-x86_64-linux-musl/maddy mail_server/
rm -rf maddy-0.8.1-x86_64-linux-musl*

# Create state directories
mkdir -p mail_server/state mail_server/runtime
```

### Configuration

Create `mail_server/maddy.conf` with these key settings:

| Setting | Value |
|---------|-------|
| `primary_domain` | `mail.local` |
| `state_dir` | `/absolute/path/to/mail_server/state` |
| `runtime_dir` | `/absolute/path/to/mail_server/runtime` |
| `tls` | `off` (for local testing) |

**Ports (non-root):**
- SMTP: `2525`
- Submission: `2587`
- IMAP: `2143`

### Option B: System-Wide Installation (Root)

> **Note:** Requires `sudo` access. Uses standard ports (25, 587, 143).

```bash
# Download & extract
wget https://github.com/foxcpp/maddy/releases/download/v0.8.1/maddy-0.8.1-x86_64-linux-musl.tar.zst
tar -I zstd -xvf maddy-0.8.1-x86_64-linux-musl.tar.zst

# Install binary
sudo mv maddy-0.8.1-x86_64-linux-musl/maddy /usr/local/bin/maddy

# Create maddy user
sudo useradd -r -s /usr/bin/nologin maddy

# Create directories
sudo mkdir -p /etc/maddy /var/lib/maddy /run/maddy
sudo chown maddy:maddy /var/lib/maddy /run/maddy

# Install config
sudo cp maddy-0.8.1-x86_64-linux-musl/maddy.conf /etc/maddy/maddy.conf

# Install systemd service
sudo cp maddy-0.8.1-x86_64-linux-musl/systemd/maddy.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable maddy

# Start service
sudo systemctl start maddy

# Create accounts
sudo maddy creds create -p "company01" company@mail.local
sudo maddy imap-acct create company@mail.local
# ... repeat for other accounts
```

**Standard Ports (root):**
- SMTP: `25`
- Submission: `587`
- IMAP: `143`
- IMAPS: `993`

**Environment for root install:**
```bash
IMAP_PORT=143
SMTP_PORT=587
```

---

## 3. Create Mail Accounts

```bash
cd mail_server

# Create accounts (creds + IMAP mailbox)
./maddy -config maddy.conf creds create -p "company01" company@mail.local
./maddy -config maddy.conf imap-acct create company@mail.local

./maddy -config maddy.conf creds create -p "support01" support@mail.local
./maddy -config maddy.conf imap-acct create support@mail.local

./maddy -config maddy.conf creds create -p "sales01" sales@mail.local
./maddy -config maddy.conf imap-acct create sales@mail.local

./maddy -config maddy.conf creds create -p "vendors01" vendors@mail.local
./maddy -config maddy.conf imap-acct create vendors@mail.local

./maddy -config maddy.conf creds create -p "hr01" hr@mail.local
./maddy -config maddy.conf imap-acct create hr@mail.local

./maddy -config maddy.conf creds create -p "it01" it@mail.local
./maddy -config maddy.conf imap-acct create it@mail.local

./maddy -config maddy.conf creds create -p "legal01" legal@mail.local
./maddy -config maddy.conf imap-acct create legal@mail.local

./maddy -config maddy.conf creds create -p "promotions01" promotions@mail.local
./maddy -config maddy.conf imap-acct create promotions@mail.local

# Verify accounts
./maddy -config maddy.conf creds list
```

---

## 4. Configure Environment

Edit `.env`:

```bash
# Email Server (Local Maddy)
IMAP_HOST=localhost
IMAP_PORT=2143
IMAP_USE_SSL=false
SMTP_HOST=localhost
SMTP_PORT=2587
SMTP_USE_TLS=false

# Main account for AI agent
EMAIL_ADDRESS=company@mail.local
EMAIL_PASSWORD=company01

# AI Provider (choose one)
OLLAMA_HOST=http://your-ollama-host:11434
OLLAMA_MODEL=qwen2.5:14b
# OR
GEMINI_API_KEY=your-api-key
```

---

## 5. Start Services

### Start Maddy

```bash
cd mail_server
nohup ./maddy -config maddy.conf > maddy.log 2>&1 &
```

### Start Web Dashboard

```bash
source .venv/bin/activate
python3 web_dashboard.py
```

Or use the control panel:

```bash
./control.sh
```

---

## 6. Thunderbird Setup (Optional)

### Manual Setup

Add `company@mail.local` account:
- **IMAP:** `localhost:2143` (No SSL)
- **SMTP:** `localhost:2587` (No SSL)
- **Username:** `company@mail.local`
- **Password:** `company01`

### Auto-Clone Accounts

After adding one account manually:

```bash
# Close Thunderbird first!
python3 testserver/add_thunderbird_accounts.py
```

This clones the `company` account to create all other department accounts.

---

## 7. Testing

### Send Test Emails

```bash
source .venv/bin/activate
python3 testserver/send_test_emails.py
```

### Clear All Mailboxes

```bash
python3 testserver/clear_mailboxes.py
```

### Process Emails (CLI)

```bash
python3 cli.py run
```

---

## Quick Reference

| Service | Host | Port |
|---------|------|------|
| IMAP | localhost | 2143 |
| SMTP Submission | localhost | 2587 |
| SMTP (external) | localhost | 2525 |
| Web Dashboard | localhost | 5000 |

| Account | Password |
|---------|----------|
| company@mail.local | company01 |
| support@mail.local | support01 |
| sales@mail.local | sales01 |
| vendors@mail.local | vendors01 |
| hr@mail.local | hr01 |
| it@mail.local | it01 |
| legal@mail.local | legal01 |
| promotions@mail.local | promotions01 |

---

## Control Panel

Interactive management:

```bash
./control.sh
```

**Options:**
1. Clear all mailboxes
2. Send sample emails
3. Process inbox once
4. Start web dashboard
5. Stop web dashboard
9. Start Maddy
10. Stop Maddy
12. Show status
