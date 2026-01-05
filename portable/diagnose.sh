#!/bin/bash
# Diagnostic script for mail setup issues

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "  AI Mail Agent - Diagnostic Check"
echo "=========================================="
echo ""

# 1. Check Maddy service
echo "1. Maddy Service:"
if systemctl is-active --quiet maddy 2>/dev/null; then
    echo -e "   ${GREEN}✓ Maddy is running${NC}"
else
    echo -e "   ${RED}✗ Maddy is NOT running${NC}"
    echo "   Try: sudo systemctl start maddy"
    echo ""
    echo "   Last error:"
    sudo journalctl -u maddy -n 5 --no-pager 2>/dev/null | tail -3
fi
echo ""

# 2. Check ports
echo "2. Port Status:"
for port in 25 143 587 993; do
    if ss -tuln | grep -q ":$port "; then
        echo -e "   ${GREEN}✓ Port $port: Open${NC}"
    else
        echo -e "   ${RED}✗ Port $port: Closed${NC}"
    fi
done
echo ""

# 3. Check mail accounts
echo "3. Mail Accounts:"
ACCOUNTS=$(sudo maddy creds list 2>/dev/null | wc -l)
if [ "$ACCOUNTS" -gt 0 ]; then
    echo -e "   ${GREEN}✓ $ACCOUNTS accounts found${NC}"
    sudo maddy creds list 2>/dev/null | while read acc; do
        echo "     - $acc"
    done
else
    echo -e "   ${RED}✗ No accounts found${NC}"
    echo "   Run: sudo ./setup.sh accounts"
fi
echo ""

# 4. Check .env file
echo "4. Configuration (.env):"
if [ -f ".env" ]; then
    echo -e "   ${GREEN}✓ .env file exists${NC}"
    grep -E "^(IMAP|SMTP|EMAIL)" .env 2>/dev/null | head -6
else
    echo -e "   ${RED}✗ .env file missing${NC}"
    echo "   Run: cp .env.example .env"
fi
echo ""

# 5. Check SSL certs
echo "5. SSL Certificates:"
if [ -f "/etc/maddy/certs/fullchain.pem" ]; then
    echo -e "   ${GREEN}✓ Certificates exist${NC}"
    EXPIRY=$(openssl x509 -enddate -noout -in /etc/maddy/certs/fullchain.pem 2>/dev/null | cut -d= -f2)
    echo "   Expires: $EXPIRY"
else
    echo -e "   ${RED}✗ Certificates missing${NC}"
    echo "   Run setup.sh to generate certs"
fi
echo ""

# 6. Test IMAP connection
echo "6. IMAP Connection Test:"
if command -v nc &>/dev/null; then
    RESULT=$(echo "A001 LOGOUT" | nc -w 2 localhost 143 2>/dev/null | head -1)
    if [[ "$RESULT" == *"OK"* ]]; then
        echo -e "   ${GREEN}✓ IMAP responding${NC}"
    else
        echo -e "   ${RED}✗ IMAP not responding${NC}"
    fi
else
    echo -e "   ${YELLOW}! nc not installed, skipping${NC}"
fi
echo ""

# 7. Test SMTP connection
echo "7. SMTP Connection Test:"
if command -v nc &>/dev/null; then
    RESULT=$(echo "QUIT" | nc -w 2 localhost 587 2>/dev/null | head -1)
    if [[ "$RESULT" == *"220"* ]]; then
        echo -e "   ${GREEN}✓ SMTP responding${NC}"
    else
        echo -e "   ${RED}✗ SMTP not responding${NC}"
    fi
fi
echo ""

# 8. Python environment
echo "8. Python Environment:"
if [ -d ".venv" ]; then
    echo -e "   ${GREEN}✓ Virtual environment exists${NC}"
else
    echo -e "   ${RED}✗ Virtual environment missing${NC}"
    echo "   Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
fi
echo ""

# Summary
echo "=========================================="
echo "  Recommendation"
echo "=========================================="
if ! systemctl is-active --quiet maddy 2>/dev/null; then
    echo -e "Run: ${YELLOW}sudo ./setup.sh${NC}"
    echo "This will install Maddy, create accounts, and configure everything."
elif [ "$ACCOUNTS" -eq 0 ]; then
    echo -e "Run: ${YELLOW}sudo ./setup.sh accounts${NC}"
    echo "This will create mail accounts."
else
    echo -e "${GREEN}System looks OK!${NC}"
    if [ -f "./start.sh" ]; then
        echo "Try: ./start.sh to start the dashboard"
    else
        echo "Try: ./start_dashboard.sh to start the dashboard"
    fi
fi
echo ""
