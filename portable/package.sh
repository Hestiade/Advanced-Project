#!/bin/bash
# =============================================================================
# Package Essential Files for Deployment
# Creates a minimal distribution of the AI Mail Redirection Agent
# =============================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Output directory name
PACKAGE_NAME="mail-agent-deploy"
OUTPUT_DIR="$SCRIPT_DIR/$PACKAGE_NAME"
ARCHIVE_NAME="${PACKAGE_NAME}.tar.gz"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       AI Mail Redirection Agent - Packager               ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Clean previous package
if [ -d "$OUTPUT_DIR" ]; then
    echo -e "${YELLOW}Removing previous package directory...${NC}"
    rm -rf "$OUTPUT_DIR"
fi

if [ -f "$ARCHIVE_NAME" ]; then
    rm -f "$ARCHIVE_NAME"
fi

# Create package directory
echo -e "${GREEN}Creating package directory...${NC}"
mkdir -p "$OUTPUT_DIR"

# =============================================================================
# Copy Essential Files
# =============================================================================

echo -e "${GREEN}Copying essential files...${NC}"

# Core application
cp web_dashboard.py "$OUTPUT_DIR/"
cp email_logger.py "$OUTPUT_DIR/"
cp requirements.txt "$OUTPUT_DIR/"
cp setup.sh "$OUTPUT_DIR/"
cp control.sh "$OUTPUT_DIR/"
cp status.sh "$OUTPUT_DIR/"
cp diagnose.sh "$OUTPUT_DIR/"

# Configuration templates (copy example, user creates .env)
cp .env.example "$OUTPUT_DIR/"
cp config.yaml "$OUTPUT_DIR/config.yaml"

# Copy mail_agent package (excluding __pycache__)
echo -e "${GREEN}Copying mail_agent package...${NC}"
mkdir -p "$OUTPUT_DIR/mail_agent"
rsync -a --exclude='__pycache__' --exclude='*.pyc' mail_agent/ "$OUTPUT_DIR/mail_agent/"

# Copy testserver (for maddy config and test emails)
echo -e "${GREEN}Copying testserver files...${NC}"
mkdir -p "$OUTPUT_DIR/testserver/samples"
cp testserver/maddy.conf "$OUTPUT_DIR/testserver/"
cp testserver/send_test_emails.py "$OUTPUT_DIR/testserver/"
cp testserver/clear_mailboxes.py "$OUTPUT_DIR/testserver/" 2>/dev/null || true

# Copy sample emails
if [ -d "testserver/samples" ]; then
    cp testserver/samples/*.txt "$OUTPUT_DIR/testserver/samples/" 2>/dev/null || true
fi

# Create empty logs directory
mkdir -p "$OUTPUT_DIR/logs"
touch "$OUTPUT_DIR/logs/.gitkeep"

# =============================================================================
# Create Quick Start Script
# =============================================================================

cat > "$OUTPUT_DIR/start.sh" << 'STARTSCRIPT'
#!/bin/bash
# Quick start script for AI Mail Redirection Agent

cd "$(dirname "${BASH_SOURCE[0]}")"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env from template..."
    cp .env.example .env
    echo ""
    echo "⚠️  Please edit .env with your configuration:"
    echo "   - OLLAMA_HOST: Your Ollama server address"
    echo "   - GEMINI_API_KEY: Or your Gemini API key"
    echo ""
    exit 1
fi

# Check if venv exists
if [ ! -d ".venv" ]; then
    echo "Run setup.sh first: sudo ./setup.sh"
    exit 1
fi

# Activate and run
source .venv/bin/activate
echo ""
echo "Starting web dashboard..."
echo "Open http://localhost:5000 in your browser"
echo ""
python3 web_dashboard.py
STARTSCRIPT

chmod +x "$OUTPUT_DIR/start.sh"
chmod +x "$OUTPUT_DIR/setup.sh"
chmod +x "$OUTPUT_DIR/diagnose.sh"

# =============================================================================
# Create README
# =============================================================================

cat > "$OUTPUT_DIR/README.md" << 'README'
# AI Mail Redirection Agent

Intelligent email routing powered by AI.

## Quick Setup

1. **Run the setup script** (requires sudo):
   ```bash
   sudo ./setup.sh
   ```

2. **Configure your environment**:
   ```bash
   cp .env.example .env
   nano .env  # Edit with your settings
   ```

3. **Start the web dashboard**:
   ```bash
   ./start.sh
   ```

4. **Open in browser**: http://localhost:5000

## Configuration

Edit `.env` to configure:
- `IMAP_HOST`, `IMAP_PORT` - Mail server connection
- `EMAIL_ADDRESS`, `EMAIL_PASSWORD` - Account to monitor
- `OLLAMA_HOST` or `GEMINI_API_KEY` - AI provider

Edit `config.yaml` to configure email routing rules.

## Files

| File | Description |
|------|-------------|
| `setup.sh` | Complete installation script |
| `start.sh` | Quick start the web dashboard |
| `web_dashboard.py` | Main web application |
| `config.yaml` | Email routing rules |
| `.env` | Environment configuration |
| `diagnose.sh` | Troubleshooting tool |

## Requirements

- Linux (Ubuntu/Debian)
- Python 3.10+
- Maddy Mail Server (installed by setup.sh)
- Ollama or Gemini API access
README

# =============================================================================
# Create Archive
# =============================================================================

echo -e "${GREEN}Creating archive...${NC}"
tar --exclude='*.pyc' --exclude='__pycache__' -czvf "$ARCHIVE_NAME" "$PACKAGE_NAME"

# Calculate sizes
DIR_SIZE=$(du -sh "$OUTPUT_DIR" | cut -f1)
ARCHIVE_SIZE=$(du -sh "$ARCHIVE_NAME" | cut -f1)

# =============================================================================
# Summary
# =============================================================================

echo ""
echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Package created successfully!${NC}"
echo ""
echo -e "  Directory: ${GREEN}$OUTPUT_DIR${NC} ($DIR_SIZE)"
echo -e "  Archive:   ${GREEN}$ARCHIVE_NAME${NC} ($ARCHIVE_SIZE)"
echo ""
echo -e "${BLUE}Contents:${NC}"
find "$OUTPUT_DIR" -type f | sed "s|$OUTPUT_DIR/|  |" | head -30
echo ""
echo -e "${BLUE}To deploy:${NC}"
echo "  1. Copy $ARCHIVE_NAME to target machine"
echo "  2. Extract: tar -xzvf $ARCHIVE_NAME"
echo "  3. Run: cd $PACKAGE_NAME && sudo ./setup.sh"
echo "  4. Configure: cp .env.example .env && nano .env"
echo "  5. Start: ./start.sh"
echo ""
echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
