#!/bin/bash
# =============================================================================
# AI Mail Redirection Agent - Complete Setup Script
# System-wide installation with Maddy Mail Server (standard ports)
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="mail.local"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MADDY_VERSION="0.8.1"
MADDY_URL="https://github.com/foxcpp/maddy/releases/download/v${MADDY_VERSION}/maddy-${MADDY_VERSION}-x86_64-linux-musl.tar.zst"

# Mail accounts to create
declare -A ACCOUNTS=(
    ["company"]="company01"
    ["support"]="support01"
    ["sales"]="sales01"
    ["vendors"]="vendors01"
    ["hr"]="hr01"
    ["it"]="it01"
    ["legal"]="legal01"
    ["promotions"]="promotions01"
    ["spam"]="spam01"
)

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

print_header() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_step() {
    echo -e "${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root (sudo)"
        echo "Usage: sudo $0"
        exit 1
    fi
}

get_ip() {
    hostname -I | awk '{print $1}'
}

# -----------------------------------------------------------------------------
# Pre-flight Checks
# -----------------------------------------------------------------------------

preflight_checks() {
    print_header "Pre-flight Checks"
    
    # Check for required tools
    local missing_tools=()
    
    for tool in wget tar zstd openssl python3 curl; do
        if ! command -v $tool &> /dev/null; then
            missing_tools+=($tool)
        else
            print_success "$tool is installed"
        fi
    done
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        echo ""
        print_step "Installing missing dependencies..."
        apt-get update
        apt-get install -y "${missing_tools[@]}"
    fi
    
    # Check Python version
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    if (( $(echo "$PYTHON_VERSION >= 3.10" | bc -l) )); then
        print_success "Python $PYTHON_VERSION installed (>= 3.10 required)"
    else
        print_error "Python 3.10+ required, found $PYTHON_VERSION"
        exit 1
    fi
    
    # Check for conflicting services
    print_step "Checking for conflicting mail services..."
    for service in postfix dovecot exim4 sendmail; do
        if systemctl is-active --quiet $service 2>/dev/null; then
            print_warning "Stopping conflicting service: $service"
            systemctl stop $service
            systemctl disable $service
        fi
    done
    print_success "No conflicting services running"
}

# -----------------------------------------------------------------------------
# Python Environment Setup
# -----------------------------------------------------------------------------

setup_python_env() {
    print_header "Setting Up Python Environment"
    
    cd "$PROJECT_DIR"
    
    # Remove existing venv if corrupted
    if [ -d ".venv" ] && [ ! -f ".venv/bin/pip" ]; then
        print_warning "Removing corrupted virtual environment..."
        rm -rf .venv
    fi
    
    # Create virtual environment
    if [ ! -d ".venv" ]; then
        print_step "Creating virtual environment..."
        python3 -m venv --without-pip .venv
        
        print_step "Bootstrapping pip..."
        curl -sS https://bootstrap.pypa.io/get-pip.py -o get-pip.py
        .venv/bin/python3 get-pip.py --quiet
        rm get-pip.py
        print_success "Virtual environment created"
    else
        print_success "Virtual environment already exists"
    fi
    
    # Install dependencies
    print_step "Installing Python dependencies..."
    .venv/bin/pip install --quiet --upgrade pip
    .venv/bin/pip install --quiet -r requirements.txt
    print_success "Python dependencies installed"
}

# -----------------------------------------------------------------------------
# Maddy Mail Server Installation
# -----------------------------------------------------------------------------

install_maddy() {
    print_header "Installing Maddy Mail Server"
    
    # Check if already installed
    if command -v maddy &> /dev/null; then
        print_success "Maddy already installed at $(which maddy)"
        return 0
    fi
    
    cd /tmp
    
    # Download Maddy
    print_step "Downloading Maddy v${MADDY_VERSION}..."
    wget -q --show-progress "$MADDY_URL" -O maddy.tar.zst
    
    # Extract
    print_step "Extracting..."
    tar -I zstd -xf maddy.tar.zst
    
    # Install binary
    print_step "Installing to /usr/local/bin/..."
    mv "maddy-${MADDY_VERSION}-x86_64-linux-musl/maddy" /usr/local/bin/maddy
    chmod +x /usr/local/bin/maddy
    
    # Cleanup
    rm -rf maddy.tar.zst "maddy-${MADDY_VERSION}-x86_64-linux-musl"
    
    print_success "Maddy installed to /usr/local/bin/maddy"
}

# -----------------------------------------------------------------------------
# Create Maddy User and Directories
# -----------------------------------------------------------------------------

setup_maddy_user() {
    print_header "Setting Up Maddy User & Directories"
    
    # Create maddy user if not exists
    if ! id "maddy" &>/dev/null; then
        print_step "Creating maddy user..."
        useradd -r -s /usr/sbin/nologin maddy
        print_success "User 'maddy' created"
    else
        print_success "User 'maddy' already exists"
    fi
    
    # Create directories
    print_step "Creating directories..."
    mkdir -p /etc/maddy/certs
    mkdir -p /var/lib/maddy
    mkdir -p /run/maddy
    
    # Set permissions
    chown -R maddy:maddy /var/lib/maddy
    chown -R maddy:maddy /run/maddy
    
    print_success "Directories created and permissions set"
}

# -----------------------------------------------------------------------------
# Generate SSL Certificates
# -----------------------------------------------------------------------------

generate_ssl_certs() {
    print_header "Generating SSL Certificates"
    
    local IP=$(get_ip)
    
    if [ -f "/etc/maddy/certs/fullchain.pem" ] && [ -f "/etc/maddy/certs/privkey.pem" ]; then
        print_warning "Existing certificates found"
        read -p "Regenerate certificates? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_success "Keeping existing certificates"
            return 0
        fi
    fi
    
    print_step "Generating self-signed certificate for $DOMAIN..."
    openssl req -x509 -newkey rsa:4096 -sha256 -days 365 -nodes \
        -keyout /etc/maddy/certs/privkey.pem \
        -out /etc/maddy/certs/fullchain.pem \
        -subj "/CN=$DOMAIN" \
        -addext "subjectAltName=DNS:$DOMAIN,DNS:localhost,IP:$IP,IP:127.0.0.1" \
        2>/dev/null
    
    chmod 600 /etc/maddy/certs/privkey.pem
    chown maddy:maddy /etc/maddy/certs/*.pem
    
    print_success "SSL certificates generated"
    echo "  Certificate: /etc/maddy/certs/fullchain.pem"
    echo "  Private Key: /etc/maddy/certs/privkey.pem"
}

# -----------------------------------------------------------------------------
# Install Maddy Configuration
# -----------------------------------------------------------------------------

install_maddy_config() {
    print_header "Installing Maddy Configuration"
    
    if [ -f "$PROJECT_DIR/testserver/maddy.conf" ]; then
        print_step "Copying configuration from project..."
        cp "$PROJECT_DIR/testserver/maddy.conf" /etc/maddy/maddy.conf
    else
        print_step "Creating default configuration..."
        cat > /etc/maddy/maddy.conf << 'MADDYCONF'
# Maddy Mail Server Configuration
# System-wide installation with standard ports

$(hostname) = mail.local
$(primary_domain) = mail.local
$(local_domains) = $(primary_domain)

state_dir /var/lib/maddy
runtime_dir /run/maddy

tls file /etc/maddy/certs/fullchain.pem /etc/maddy/certs/privkey.pem

# Message storage
storage.imapsql local_mailboxes {
    driver sqlite3
    dsn imapsql.db
}

# Auth table
auth.pass_table local_authdb {
    table sql_table {
        driver sqlite3
        dsn credentials.db
        table_name passwords
    }
}

# IMAP with TLS (ports 993 and 143)
imap tls://0.0.0.0:993 tcp://0.0.0.0:143 {
    auth &local_authdb
    storage &local_mailboxes
}

# Local delivery target
target.queue local_queue {
    hostname $(hostname)
    target &local_mailboxes
}

# SMTP - receiving mail (port 25)
smtp tcp://0.0.0.0:25 {
    hostname $(hostname)
    
    default_source {
        destination $(local_domains) {
            deliver_to &local_queue
        }
        default_destination {
            reject 550 5.1.1 "User not found"
        }
    }
}

# SMTP submission (port 587)
submission tcp://0.0.0.0:587 {
    hostname $(hostname)
    
    auth &local_authdb
    
    default_source {
        destination $(local_domains) {
            deliver_to &local_queue
        }
        default_destination {
            reject 550 5.1.1 "User not local"
        }
    }
}
MADDYCONF
    fi
    
    chown maddy:maddy /etc/maddy/maddy.conf
    print_success "Configuration installed to /etc/maddy/maddy.conf"
}

# -----------------------------------------------------------------------------
# Install Systemd Service
# -----------------------------------------------------------------------------

install_systemd_service() {
    print_header "Installing Systemd Service"
    
    print_step "Creating maddy.service..."
    cat > /etc/systemd/system/maddy.service << 'EOF'
[Unit]
Description=Maddy Mail Server
Documentation=https://maddy.email
After=network.target

[Service]
Type=simple
User=maddy
Group=maddy
ExecStart=/usr/local/bin/maddy --config /etc/maddy/maddy.conf run
Restart=on-failure
RestartSec=5

RuntimeDirectory=maddy
StateDirectory=maddy

# Allow binding to privileged ports (25, 143, 587, 993)
AmbientCapabilities=CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_BIND_SERVICE

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/var/lib/maddy /run/maddy

[Install]
WantedBy=multi-user.target
EOF

    print_step "Reloading systemd..."
    systemctl daemon-reload
    
    print_step "Enabling maddy service..."
    systemctl enable maddy
    
    print_success "Systemd service installed"
}

# -----------------------------------------------------------------------------
# Start Maddy and Create Accounts
# -----------------------------------------------------------------------------

start_maddy_and_create_accounts() {
    print_header "Starting Maddy & Creating Accounts"
    
    # Start/restart maddy
    print_step "Starting Maddy mail server..."
    systemctl restart maddy
    sleep 2
    
    if systemctl is-active --quiet maddy; then
        print_success "Maddy is running"
    else
        print_error "Maddy failed to start!"
        journalctl -u maddy -n 20 --no-pager
        exit 1
    fi
    
    # Create mail accounts
    print_step "Creating mail accounts..."
    for account in "${!ACCOUNTS[@]}"; do
        local email="${account}@${DOMAIN}"
        local password="${ACCOUNTS[$account]}"
        
        # Check if account exists
        if maddy creds list 2>/dev/null | grep -q "$email"; then
            print_success "Account $email already exists"
        else
            print_step "Creating $email..."
            echo "$password" | maddy creds create "$email" 2>/dev/null || true
            maddy imap-acct create "$email" 2>/dev/null || true
            print_success "Created $email"
        fi
    done
    
    echo ""
    print_success "All accounts created"
}

# -----------------------------------------------------------------------------
# Create Environment File
# -----------------------------------------------------------------------------

create_env_file() {
    print_header "Creating Environment Configuration"
    
    cd "$PROJECT_DIR"
    
    if [ -f ".env" ]; then
        print_warning ".env file already exists"
        read -p "Overwrite with default configuration? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_success "Keeping existing .env"
            return 0
        fi
    fi
    
    print_step "Creating .env file..."
    cat > .env << 'ENVFILE'
# Email Server Configuration (Maddy Mail Server - System Install)
IMAP_HOST=localhost
IMAP_PORT=143
IMAP_USE_SSL=false
SMTP_HOST=localhost
SMTP_PORT=587
SMTP_USE_TLS=true

# Email Credentials (company inbox - monitored by AI agent)
EMAIL_ADDRESS=company@mail.local
EMAIL_PASSWORD=company01

# AI Provider: Ollama (update with your Ollama host)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen3:14b

# Option 2: Google Gemini (requires API key)
GEMINI_API_KEY=
ENVFILE

    # Set ownership to the original user (not root)
    local REAL_USER="${SUDO_USER:-$USER}"
    chown "$REAL_USER:$REAL_USER" .env
    
    print_success ".env file created"
    print_warning "Remember to update OLLAMA_HOST with your Ollama server address!"
}

# -----------------------------------------------------------------------------
# Update /etc/hosts
# -----------------------------------------------------------------------------

update_hosts_file() {
    print_header "Updating /etc/hosts"
    
    if grep -q "$DOMAIN" /etc/hosts; then
        print_success "$DOMAIN already in /etc/hosts"
    else
        print_step "Adding $DOMAIN to /etc/hosts..."
        echo "127.0.0.1    $DOMAIN" >> /etc/hosts
        print_success "Added: 127.0.0.1    $DOMAIN"
    fi
}

# -----------------------------------------------------------------------------
# Verify Installation
# -----------------------------------------------------------------------------

verify_installation() {
    print_header "Verifying Installation"
    
    local IP=$(get_ip)
    local errors=0
    
    # Check Maddy service
    print_step "Checking Maddy service..."
    if systemctl is-active --quiet maddy; then
        print_success "Maddy service is running"
    else
        print_error "Maddy service is not running"
        ((errors++))
    fi
    
    # Check ports
    print_step "Checking network ports..."
    for port in 25 143 587 993; do
        if ss -tlnp | grep -q ":$port "; then
            print_success "Port $port is listening"
        else
            print_error "Port $port is NOT listening"
            ((errors++))
        fi
    done
    
    # Check Python environment
    print_step "Checking Python environment..."
    if [ -f "$PROJECT_DIR/.venv/bin/python3" ]; then
        print_success "Python venv exists"
    else
        print_error "Python venv missing"
        ((errors++))
    fi
    
    # Test IMAP connection
    print_step "Testing IMAP connection..."
    if timeout 2 bash -c "echo -e 'a001 LOGOUT\n' | nc -q1 localhost 143" &>/dev/null; then
        print_success "IMAP connection successful"
    else
        print_warning "IMAP connection test failed (may need a moment to start)"
    fi
    
    echo ""
    if [ $errors -eq 0 ]; then
        print_success "All checks passed!"
    else
        print_error "$errors check(s) failed"
    fi
    
    return $errors
}

# -----------------------------------------------------------------------------
# Print Summary
# -----------------------------------------------------------------------------

print_summary() {
    local IP=$(get_ip)
    
    print_header "Setup Complete!"
    
    echo -e "${GREEN}Mail Server Configuration:${NC}"
    echo "  ├─ Domain:      $DOMAIN"
    echo "  ├─ IP Address:  $IP"
    echo "  ├─ SMTP:        Port 25 (receiving), 587 (submission)"
    echo "  ├─ IMAP:        Port 143 (STARTTLS), 993 (SSL/TLS)"
    echo "  └─ Config:      /etc/maddy/maddy.conf"
    echo ""
    
    echo -e "${GREEN}Mail Accounts:${NC}"
    for account in "${!ACCOUNTS[@]}"; do
        echo "  ├─ ${account}@${DOMAIN} : ${ACCOUNTS[$account]}"
    done
    echo ""
    
    echo -e "${GREEN}Project Files:${NC}"
    echo "  ├─ Directory:   $PROJECT_DIR"
    echo "  ├─ Config:      $PROJECT_DIR/.env"
    echo "  └─ Venv:        $PROJECT_DIR/.venv/"
    echo ""
    
    echo -e "${GREEN}Quick Start Commands:${NC}"
    echo "  # Start web dashboard"
    echo "  cd $PROJECT_DIR"
    echo "  source .venv/bin/activate"
    echo "  python3 web_dashboard.py"
    echo ""
    echo "  # Or use control panel"
    echo "  ./control.sh"
    echo ""
    echo "  # Send test emails"
    echo "  python3 testserver/send_test_emails.py"
    echo ""
    
    echo -e "${GREEN}Thunderbird/Email Client Setup:${NC}"
    echo "  Server:    localhost (or $IP from other machines)"
    echo "  IMAP:      Port 143 (STARTTLS) or 993 (SSL/TLS)"
    echo "  SMTP:      Port 587 (STARTTLS)"
    echo "  Username:  company@mail.local"
    echo "  Password:  company01"
    echo ""
    
    echo -e "${YELLOW}Note: Accept the self-signed certificate when prompted.${NC}"
}

# -----------------------------------------------------------------------------
# Modular Installation Functions (grouped steps)
# -----------------------------------------------------------------------------

install_python_only() {
    print_header "Python Environment Setup Only"
    setup_python_env
    print_success "Python environment ready!"
}

install_maddy_only() {
    print_header "Maddy Installation Only"
    check_root
    preflight_checks
    install_maddy
    setup_maddy_user
    generate_ssl_certs
    install_maddy_config
    install_systemd_service
    
    # Start service
    systemctl restart maddy
    sleep 2
    if systemctl is-active --quiet maddy; then
        print_success "Maddy installed and running!"
    else
        print_error "Maddy failed to start"
        exit 1
    fi
}

create_accounts_only() {
    print_header "Creating Mail Accounts Only"
    check_root
    
    if ! systemctl is-active --quiet maddy; then
        print_error "Maddy is not running. Start it first: sudo systemctl start maddy"
        exit 1
    fi
    
    for account in "${!ACCOUNTS[@]}"; do
        local email="${account}@${DOMAIN}"
        local password="${ACCOUNTS[$account]}"
        
        if maddy creds list 2>/dev/null | grep -q "$email"; then
            print_success "Account $email already exists"
        else
            print_step "Creating $email..."
            echo "$password" | maddy creds create "$email" 2>/dev/null || true
            maddy imap-acct create "$email" 2>/dev/null || true
            print_success "Created $email"
        fi
    done
    
    print_success "All accounts ready!"
}

setup_env_only() {
    print_header "Environment Configuration Only"
    create_env_file
    update_hosts_file
    print_success "Environment configured!"
}

run_full_setup() {
    print_header "AI Mail Redirection Agent - Full Setup"
    echo "This script will set up the AI mail redirection agent."
    echo "Project Directory: $PROJECT_DIR"
    echo ""
    
    check_root
    
    # Ask about Maddy installation
    echo -e "${YELLOW}Do you want to install Maddy mail server?${NC}"
    echo "  [Y] Yes - Install Maddy for local mail testing"
    echo "  [N] No  - Client only (connect to external mail server)"
    echo ""
    read -p "Install Maddy? [Y/n]: " install_maddy_choice
    install_maddy_choice=${install_maddy_choice:-Y}
    
    INSTALL_MADDY=false
    if [[ "$install_maddy_choice" =~ ^[Yy]$ ]]; then
        INSTALL_MADDY=true
    fi
    
    preflight_checks
    setup_python_env
    
    if [ "$INSTALL_MADDY" = true ]; then
        install_maddy
        setup_maddy_user
        generate_ssl_certs
        install_maddy_config
        install_systemd_service
        start_maddy_and_create_accounts
    else
        print_header "Skipping Maddy Installation"
        print_warning "Configure .env with your external mail server settings"
    fi
    
    create_env_file
    update_hosts_file
    
    if [ "$INSTALL_MADDY" = true ]; then
        verify_installation
        print_summary
    else
        print_summary_client_only
    fi
}

print_summary_client_only() {
    local IP=$(get_ip)
    
    print_header "Client-Only Setup Complete!"
    
    echo -e "${GREEN}Project Files:${NC}"
    echo "  ├─ Directory:   $PROJECT_DIR"
    echo "  ├─ Config:      $PROJECT_DIR/.env"
    echo "  └─ Venv:        $PROJECT_DIR/.venv/"
    echo ""
    
    echo -e "${YELLOW}⚠ Configure your mail server in .env:${NC}"
    echo "  IMAP_HOST=imap.gmail.com"
    echo "  IMAP_PORT=993"
    echo "  IMAP_USE_SSL=true"
    echo "  EMAIL_ADDRESS=your-email@gmail.com"
    echo "  EMAIL_PASSWORD=your-app-password"
    echo ""
    
    echo -e "${GREEN}Quick Start Commands:${NC}"
    echo "  cd $PROJECT_DIR"
    echo "  nano .env  # Configure your mail server"
    echo "  ./start.sh"
    echo ""
}

# -----------------------------------------------------------------------------
# Usage / Help
# -----------------------------------------------------------------------------

show_usage() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "AI Mail Redirection Agent - Modular Setup Script"
    echo ""
    echo "Commands:"
    echo "  all        Full installation (default) - requires sudo"
    echo "  python     Set up Python virtual environment only"
    echo "  maddy      Install and configure Maddy mail server - requires sudo"
    echo "  accounts   Create mail accounts only - requires sudo"
    echo "  env        Create .env and update /etc/hosts - requires sudo"
    echo "  verify     Verify installation status"
    echo "  status     Show current service status"
    echo "  help       Show this help message"
    echo ""
    echo "Examples:"
    echo "  sudo $0              # Full installation"
    echo "  sudo $0 all          # Full installation (explicit)"
    echo "  $0 python            # Python venv setup (no sudo needed)"
    echo "  sudo $0 maddy        # Install Maddy only"
    echo "  sudo $0 accounts     # Create accounts only"
    echo "  $0 verify            # Check installation"
    echo ""
}

show_status() {
    print_header "Service Status"
    
    local IP=$(get_ip)
    
    # Maddy service
    echo -e "${BLUE}Maddy Service:${NC}"
    if systemctl is-active --quiet maddy 2>/dev/null; then
        print_success "Running"
        echo "  PID: $(pgrep -f 'maddy' | head -1)"
    else
        print_error "Not running"
    fi
    echo ""
    
    # Ports
    echo -e "${BLUE}Network Ports:${NC}"
    for port in 25 143 587 993; do
        if ss -tlnp 2>/dev/null | grep -q ":$port "; then
            print_success "Port $port: listening"
        else
            print_error "Port $port: not listening"
        fi
    done
    echo ""
    
    # Accounts
    echo -e "${BLUE}Mail Accounts:${NC}"
    if command -v maddy &>/dev/null; then
        maddy creds list 2>/dev/null || echo "  Unable to list accounts"
    else
        echo "  Maddy not installed"
    fi
    echo ""
    
    # Python
    echo -e "${BLUE}Python Environment:${NC}"
    if [ -f "$PROJECT_DIR/.venv/bin/python3" ]; then
        print_success "Virtual environment exists"
        echo "  Python: $($PROJECT_DIR/.venv/bin/python3 --version)"
    else
        print_error "Virtual environment not found"
    fi
    echo ""
    
    # Config
    echo -e "${BLUE}Configuration:${NC}"
    [ -f "$PROJECT_DIR/.env" ] && print_success ".env exists" || print_error ".env missing"
    [ -f "/etc/maddy/maddy.conf" ] && print_success "maddy.conf exists" || print_error "maddy.conf missing"
    [ -f "/etc/maddy/certs/fullchain.pem" ] && print_success "SSL cert exists" || print_error "SSL cert missing"
}

# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------

main() {
    local command="${1:-all}"
    
    case "$command" in
        all)
            run_full_setup
            ;;
        python)
            install_python_only
            ;;
        maddy)
            install_maddy_only
            ;;
        accounts)
            create_accounts_only
            ;;
        env)
            check_root
            setup_env_only
            ;;
        verify)
            verify_installation
            ;;
        status)
            show_status
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            print_error "Unknown command: $command"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
