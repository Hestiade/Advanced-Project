#!/bin/bash
# Interactive Control Panel for AI Mail Redirection Agent

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Load .env file
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Debug mode (hidden test options by default)
DEBUG_MODE=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m'

show_menu() {
    clear
    # Get SSH info
    SSH_USER=$(whoami)
    SSH_HOST=$(hostname)
    SSH_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║       AI Mail Redirection Agent - Control Panel          ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
    echo -e "  ${CYAN}SSH:${NC} ${SSH_USER}@${SSH_HOST} (${SSH_IP})"
    if $DEBUG_MODE; then
        echo -e "  ${YELLOW}[DEBUG MODE ON]${NC}"
    fi
    echo ""
    
    # Debug options (only shown in debug mode)
    if $DEBUG_MODE; then
        echo -e "${YELLOW}━━━ Debug / Testing ━━━${NC}"
        echo -e "  ${YELLOW}1${NC}) Clear all mailboxes"
        echo -e "  ${YELLOW}2${NC}) Send sample emails"
        echo -e "  ${YELLOW}3${NC}) Process inbox once (CLI)"
        echo ""
    fi
    
    echo -e "${CYAN}━━━ Dashboard ━━━${NC}"
    echo -e "  ${GREEN}4${NC}) Start web dashboard"
    echo -e "  ${GREEN}5${NC}) Stop web dashboard"
    echo -e "  ${GREEN}6${NC}) Open dashboard in browser"
    echo -e "  ${GREEN}7${NC}) Start email watching"
    echo -e "  ${GREEN}8${NC}) Stop email watching"
    echo ""
    echo -e "${CYAN}━━━ Mail Server (Maddy) ━━━${NC}"
    echo -e "  ${GREEN}9${NC}) Start Maddy"
    echo -e "  ${GREEN}10${NC}) Stop Maddy"
    echo -e "  ${GREEN}11${NC}) Restart Maddy"
    echo ""
    echo -e "${CYAN}━━━ System ━━━${NC}"
    echo -e "  ${GREEN}12${NC}) Show status"
    echo -e "  ${GREEN}13${NC}) View Maddy logs"
    echo -e "  ${GREEN}14${NC}) List mail accounts"
    echo -e "  ${GREEN}15${NC}) View email logs"
    echo ""
    
    # Show TLS status
    TLS_STATUS=$(grep "^IMAP_USE_STARTTLS=" .env 2>/dev/null | cut -d= -f2)
    if [ "$TLS_STATUS" = "true" ]; then
        echo -e "  ${GRAY}t${NC}) Toggle TLS  [${GREEN}ON${NC}]"
    else
        echo -e "  ${GRAY}t${NC}) Toggle TLS  [${RED}OFF${NC}]"
    fi
    echo -e "  ${GRAY}d${NC}) Toggle debug mode"
    echo -e "  ${RED}0${NC}) Exit"
    echo ""
    echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
}

press_enter() {
    echo ""
    read -p "Press Enter to continue..."
}

# 1. Clear all mailboxes
clear_mailboxes() {
    echo -e "${YELLOW}Clearing all mailboxes...${NC}"
    source .venv/bin/activate
    python3 testserver/clear_mailboxes.py
    press_enter
}

# 2. Send sample emails
send_samples() {
    echo -e "${YELLOW}Sending sample emails...${NC}"
    source .venv/bin/activate
    python3 testserver/send_test_emails.py
    press_enter
}

# 3. Process inbox once (CLI)
process_inbox() {
    echo -e "${GREEN}Processing inbox...${NC}"
    source .venv/bin/activate
    python3 cli.py run
    press_enter
}

# 3. Start web dashboard
start_dashboard() {
    if pgrep -f "web_dashboard.py" > /dev/null; then
        echo -e "${YELLOW}Dashboard is already running!${NC}"
    else
        echo -e "${GREEN}Starting web dashboard...${NC}"
        source .venv/bin/activate
        nohup python3 web_dashboard.py > /tmp/dashboard.log 2>&1 &
        sleep 2
        if pgrep -f "web_dashboard.py" > /dev/null; then
            echo -e "${GREEN}Dashboard started!${NC}"
            echo -e "URL: ${CYAN}http://localhost:5000${NC}"
        else
            echo -e "${RED}Failed to start dashboard. Check /tmp/dashboard.log${NC}"
        fi
    fi
    press_enter
}

# 4. Stop web dashboard
stop_dashboard() {
    if pgrep -f "web_dashboard.py" > /dev/null; then
        echo -e "${YELLOW}Stopping web dashboard...${NC}"
        pkill -f "web_dashboard.py"
        sleep 1
        echo -e "${GREEN}Dashboard stopped.${NC}"
    else
        echo -e "${YELLOW}Dashboard is not running.${NC}"
    fi
    press_enter
}

# 5. Open dashboard in browser
open_browser() {
    if pgrep -f "web_dashboard.py" > /dev/null; then
        echo -e "${GREEN}Opening dashboard in browser...${NC}"
        xdg-open http://localhost:5000 2>/dev/null || \
        open http://localhost:5000 2>/dev/null || \
        echo -e "${YELLOW}Please open http://localhost:5000 manually${NC}"
    else
        echo -e "${RED}Dashboard is not running! Start it first (option 3).${NC}"
    fi
    press_enter
}

# 7. Start email watching (via dashboard)
start_watching() {
    if ! pgrep -f "web_dashboard.py" > /dev/null; then
        echo -e "${RED}Dashboard is not running! Start it first (option 4).${NC}"
        press_enter
        return
    fi
    
    echo -e "${GREEN}Starting email watching...${NC}"
    source .venv/bin/activate
    python3 -c "
import socketio
sio = socketio.Client()
sio.connect('http://localhost:5000')
sio.emit('start')
print('✓ Start command sent to dashboard')
sio.disconnect()
" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Email watching started!${NC}"
    else
        echo -e "${RED}Failed to connect to dashboard.${NC}"
    fi
    press_enter
}

# 8. Stop email watching (via dashboard)
stop_watching() {
    if ! pgrep -f "web_dashboard.py" > /dev/null; then
        echo -e "${YELLOW}Dashboard is not running.${NC}"
        press_enter
        return
    fi
    
    echo -e "${YELLOW}Stopping email watching...${NC}"
    source .venv/bin/activate
    python3 -c "
import socketio
sio = socketio.Client()
sio.connect('http://localhost:5000')
sio.emit('stop')
print('✓ Stop command sent to dashboard')
sio.disconnect()
" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Email watching stopped!${NC}"
    else
        echo -e "${RED}Failed to connect to dashboard.${NC}"
    fi
    press_enter
}

# 6. Start Maddy
start_maddy() {
    echo -e "${GREEN}Starting Maddy mail server...${NC}"
    sudo systemctl start maddy
    sleep 1
    if systemctl is-active --quiet maddy; then
        echo -e "${GREEN}Maddy started successfully!${NC}"
    else
        echo -e "${RED}Failed to start Maddy.${NC}"
    fi
    press_enter
}

# 7. Stop Maddy
stop_maddy() {
    echo -e "${YELLOW}Stopping Maddy mail server...${NC}"
    sudo systemctl stop maddy
    sleep 1
    echo -e "${GREEN}Maddy stopped.${NC}"
    press_enter
}

# 8. Restart Maddy
restart_maddy() {
    echo -e "${YELLOW}Restarting Maddy mail server...${NC}"
    sudo systemctl restart maddy
    sleep 2
    if systemctl is-active --quiet maddy; then
        echo -e "${GREEN}Maddy restarted successfully!${NC}"
    else
        echo -e "${RED}Failed to restart Maddy.${NC}"
    fi
    press_enter
}

# 9. Show status
show_status() {
    ./status.sh
    press_enter
}

# 10. View Maddy logs
view_logs() {
    echo -e "${YELLOW}Showing last 50 lines of Maddy logs (Ctrl+C to exit)...${NC}"
    echo ""
    sudo journalctl -u maddy -n 50 --no-pager
    press_enter
}

# 11. List mail accounts
list_accounts() {
    echo -e "${CYAN}Mail Accounts:${NC}"
    echo ""
    sudo maddy creds list 2>/dev/null | nl
    echo ""
    TOTAL=$(sudo maddy creds list 2>/dev/null | wc -l)
    echo -e "Total: ${GREEN}$TOTAL${NC} accounts"
    press_enter
}

# 13. View email logs
view_email_logs() {
    echo -e "${CYAN}Email Processing Logs:${NC}"
    echo ""
    LOG_DIR="$PROJECT_DIR/logs"
    if [ -d "$LOG_DIR" ]; then
        TODAY=$(date +%Y-%m-%d)
        LOG_FILE="$LOG_DIR/email_log_$TODAY.jsonl"
        if [ -f "$LOG_FILE" ]; then
            echo -e "${GREEN}Today's log ($TODAY):${NC}"
            echo ""
            tail -20 "$LOG_FILE" | python3 -c "
import sys, json
for line in sys.stdin:
    try:
        d = json.loads(line)
        ts = d.get('timestamp', '')[:19]
        subj = d.get('subject', '')[:40]
        action = d.get('final_action', 'unknown')
        cat = d.get('ai_category', '')
        print(f'{ts} | {action:12} | {cat:12} | {subj}')
    except: pass
"
            echo ""
            TOTAL=$(wc -l < "$LOG_FILE")
            echo -e "Total entries today: ${GREEN}$TOTAL${NC}"
        else
            echo -e "${YELLOW}No logs for today yet.${NC}"
        fi
        echo ""
        echo -e "${CYAN}Available log files:${NC}"
        ls -la "$LOG_DIR"/*.jsonl 2>/dev/null | tail -5
    else
        echo -e "${YELLOW}No logs directory yet. Process some emails first.${NC}"
    fi
    press_enter
}

# Main loop
while true; do
    show_menu
    read -p "Enter choice: " choice
    echo ""
    
    case $choice in
        1) 
            if $DEBUG_MODE; then
                clear_mailboxes
            else
                echo -e "${RED}Enable debug mode first (press 'd')${NC}"
                press_enter
            fi
            ;;
        2) 
            if $DEBUG_MODE; then
                send_samples
            else
                echo -e "${RED}Enable debug mode first (press 'd')${NC}"
                press_enter
            fi
            ;;
        3) 
            if $DEBUG_MODE; then
                process_inbox
            else
                echo -e "${RED}Enable debug mode first (press 'd')${NC}"
                press_enter
            fi
            ;;
        4) start_dashboard ;;
        5) stop_dashboard ;;
        6) open_browser ;;
        7) start_watching ;;
        8) stop_watching ;;
        9) start_maddy ;;
        10) stop_maddy ;;
        11) restart_maddy ;;
        12) show_status ;;
        13) view_logs ;;
        14) list_accounts ;;
        15) view_email_logs ;;
        d|D)
            if $DEBUG_MODE; then
                DEBUG_MODE=false
                echo -e "${GREEN}Debug mode disabled${NC}"
            else
                DEBUG_MODE=true
                echo -e "${YELLOW}Debug mode enabled - test options now visible${NC}"
            fi
            sleep 1
            ;;
        t|T)
            TLS_CURRENT=$(grep "^IMAP_USE_STARTTLS=" .env 2>/dev/null | cut -d= -f2)
            if [ "$TLS_CURRENT" = "true" ]; then
                # Disable TLS  
                sed -i 's/^IMAP_USE_STARTTLS=.*/IMAP_USE_STARTTLS=false/' .env
                sed -i 's/^SMTP_USE_TLS=.*/SMTP_USE_TLS=false/' .env
                echo -e "${YELLOW}TLS disabled${NC}"
                echo -e "Note: Make sure Maddy has 'insecure_auth' enabled"
            else
                # Enable TLS
                if grep -q "^IMAP_USE_STARTTLS=" .env; then
                    sed -i 's/^IMAP_USE_STARTTLS=.*/IMAP_USE_STARTTLS=true/' .env
                else
                    echo "IMAP_USE_STARTTLS=true" >> .env
                fi
                if grep -q "^SMTP_USE_TLS=" .env; then
                    sed -i 's/^SMTP_USE_TLS=.*/SMTP_USE_TLS=true/' .env
                else
                    echo "SMTP_USE_TLS=true" >> .env
                fi
                echo -e "${GREEN}TLS enabled${NC}"
            fi
            sleep 1
            ;;
        0) 
            echo -e "${GREEN}Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option. Please try again.${NC}"
            press_enter
            ;;
    esac
done
