#!/bin/bash
# Status script for AI Mail Redirection Agent
# Shows the status of all related services and processes

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Load .env file
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       AI Mail Redirection Agent - System Status          ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to check if a service is running
check_service() {
    if systemctl is-active --quiet "$1" 2>/dev/null; then
        echo -e "  ${GREEN}●${NC} $1: ${GREEN}Running${NC}"
        return 0
    else
        echo -e "  ${RED}○${NC} $1: ${RED}Stopped${NC}"
        return 1
    fi
}

# Function to check if a process is running
check_process() {
    if pgrep -f "$1" > /dev/null 2>&1; then
        PID=$(pgrep -f "$1" | head -1)
        echo -e "  ${GREEN}●${NC} $2: ${GREEN}Running${NC} (PID: $PID)"
        return 0
    else
        echo -e "  ${RED}○${NC} $2: ${RED}Not running${NC}"
        return 1
    fi
}

# Function to check port
check_port() {
    if ss -tuln | grep -q ":$1 " 2>/dev/null; then
        echo -e "  ${GREEN}●${NC} Port $1 ($2): ${GREEN}Open${NC}"
        return 0
    else
        echo -e "  ${RED}○${NC} Port $1 ($2): ${RED}Closed${NC}"
        return 1
    fi
}

echo -e "${YELLOW}━━━ Mail Server (Maddy) ━━━${NC}"
check_service "maddy"
echo ""

echo -e "${YELLOW}━━━ Ports ━━━${NC}"
check_port 25 "SMTP"
check_port 143 "IMAP"
check_port 587 "SMTP Submission"
check_port 993 "IMAPS"
check_port 5000 "Web Dashboard"
echo ""

echo -e "${YELLOW}━━━ Application Processes ━━━${NC}"
check_process "web_dashboard.py" "Web Dashboard"
check_process "ollama" "Ollama AI"
echo ""

echo -e "${YELLOW}━━━ Mail Accounts ━━━${NC}"
if command -v maddy &> /dev/null; then
    ACCOUNTS=$(sudo maddy creds list 2>/dev/null | wc -l)
    echo -e "  ${GREEN}●${NC} Total accounts: ${GREEN}$ACCOUNTS${NC}"
    echo ""
    echo "  Accounts:"
    sudo maddy creds list 2>/dev/null | while read account; do
        echo "    - $account"
    done
else
    echo -e "  ${YELLOW}!${NC} Maddy CLI not available"
fi
echo ""

echo -e "${YELLOW}━━━ Email Stats ━━━${NC}"
cd "$PROJECT_DIR"
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate 2>/dev/null
    UNREAD=$(python3 -c "
from mail_agent import load_config, IMAPClient
config = load_config()
imap = IMAPClient(
    host=config.email.imap_host,
    port=config.email.imap_port,
    address=config.email.address,
    password=config.email.password,
    use_ssl=config.email.use_ssl,
)
try:
    with imap:
        emails = list(imap.fetch_unread())
        print(len(emails))
except:
    print('N/A')
" 2>/dev/null)
    echo -e "  ${GREEN}●${NC} Unread emails: ${GREEN}$UNREAD${NC}"
else
    echo -e "  ${YELLOW}!${NC} Python venv not found"
fi
echo ""

echo -e "${YELLOW}━━━ Ollama Status ━━━${NC}"
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5:14b}"

# Extract IP/hostname from URL for ping fallback
OLLAMA_IP=$(echo "$OLLAMA_HOST" | sed -E 's|https?://([^:/]+).*|\1|')

# Check if Ollama API is reachable (with 5 second timeout)
if curl -s --max-time 5 "$OLLAMA_HOST/api/tags" > /dev/null 2>&1; then
    echo -e "  ${GREEN}●${NC} Ollama API: ${GREEN}Connected${NC} ($OLLAMA_HOST)"
    
    # List available models
    MODELS=$(curl -s --max-time 5 "$OLLAMA_HOST/api/tags" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(', '.join([m['name'] for m in d.get('models',[])]))" 2>/dev/null)
    if [ -n "$MODELS" ]; then
        echo -e "  ${GREEN}●${NC} Models: $MODELS"
    fi
    
    # Quick ping test - send a simple prompt
    echo -e "  ${YELLOW}●${NC} Ping test: Testing $OLLAMA_MODEL..."
    PING_RESPONSE=$(curl -s --max-time 10 "$OLLAMA_HOST/api/generate" \
        -d "{\"model\":\"$OLLAMA_MODEL\",\"prompt\":\"Say OK\",\"stream\":false,\"options\":{\"num_predict\":5}}" 2>/dev/null)
    
    if echo "$PING_RESPONSE" | grep -q '"response"'; then
        PING_TEXT=$(echo "$PING_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('response','').strip()[:20])" 2>/dev/null)
        echo -e "  ${GREEN}●${NC} Ping test: ${GREEN}OK${NC} (Response: \"$PING_TEXT\")"
    else
        echo -e "  ${RED}○${NC} Ping test: ${RED}No response${NC} (Model may not be loaded)"
    fi
else
    echo -e "  ${RED}○${NC} Ollama API: ${RED}Not reachable${NC} ($OLLAMA_HOST)"
    
    # Fallback: Check if the host is at least pingable on the network
    echo -e "  ${YELLOW}●${NC} Network ping: Checking $OLLAMA_IP..."
    if ping -c 1 -W 2 "$OLLAMA_IP" > /dev/null 2>&1; then
        echo -e "  ${YELLOW}●${NC} Network ping: ${YELLOW}Host is UP${NC} (Ollama service may be stopped)"
    else
        echo -e "  ${RED}○${NC} Network ping: ${RED}Host is DOWN${NC} (Machine offline or unreachable)"
    fi
fi
echo ""

echo ""

echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
echo -e "  Dashboard URL: ${GREEN}http://localhost:5000${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
echo ""
