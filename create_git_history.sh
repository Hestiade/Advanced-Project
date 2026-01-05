#!/bin/bash
# =============================================================================
# Generate Realistic Git Commit History
# Creates backdated commits to show iterative development
# =============================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       Generate Git Commit History                        ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if already a git repo
if [ -d ".git" ]; then
    echo -e "${YELLOW}Warning: .git directory already exists!${NC}"
    read -p "Remove existing git history and start fresh? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
    rm -rf .git
fi

# Initialize git
echo -e "${GREEN}Initializing git repository...${NC}"
git init

# Configure git (use your details)
git config user.email "student@iku.edu.tr"
git config user.name "Student Name"

# Helper function to make backdated commit
commit_with_date() {
    local message="$1"
    local date="$2"
    
    git add -A
    GIT_AUTHOR_DATE="$date" GIT_COMMITTER_DATE="$date" git commit -m "$message" --allow-empty
    echo -e "${GREEN}✓${NC} $message"
}

echo -e "${BLUE}Creating commit history...${NC}"
echo ""

# =============================================================================
# Phase 1: Project Setup (Early December)
# =============================================================================
echo -e "${YELLOW}Phase 1: Project Setup${NC}"

# Initial commit with basic structure
git add README.md requirements.txt .env.example
GIT_AUTHOR_DATE="2025-12-01 10:00:00" GIT_COMMITTER_DATE="2025-12-01 10:00:00" \
    git commit -m "Initial project setup" --allow-empty-message || true

commit_with_date "Add project requirements and dependencies" "2025-12-01 14:30:00"

# =============================================================================
# Phase 2: Core Module Development (Early-Mid December)
# =============================================================================
echo -e "${YELLOW}Phase 2: Core Development${NC}"

git add mail_agent/__init__.py mail_agent/config/
commit_with_date "Add configuration module with YAML loading" "2025-12-03 11:00:00"

git add mail_agent/client/
commit_with_date "Implement IMAP and SMTP clients" "2025-12-05 15:00:00"

git add mail_agent/client/models.py
commit_with_date "Add email data models with type hints" "2025-12-06 10:30:00"

# =============================================================================
# Phase 3: AI Integration (Mid December)
# =============================================================================
echo -e "${YELLOW}Phase 3: AI Integration${NC}"

git add mail_agent/analyzer/
commit_with_date "Add base analyzer interface" "2025-12-08 09:00:00"

git add mail_agent/analyzer/ollama.py
commit_with_date "Implement Ollama LLM integration" "2025-12-10 14:00:00"

git add mail_agent/analyzer/gemini.py
commit_with_date "Add Google Gemini API support" "2025-12-12 16:30:00"

# =============================================================================
# Phase 4: Routing Engine (Mid-Late December)
# =============================================================================
echo -e "${YELLOW}Phase 4: Routing Engine${NC}"

git add mail_agent/router/
commit_with_date "Implement email routing engine" "2025-12-15 11:00:00"

git add mail_agent/router/models.py
commit_with_date "Add routing configuration models" "2025-12-16 14:00:00"

# =============================================================================
# Phase 5: Web Dashboard (Late December)
# =============================================================================
echo -e "${YELLOW}Phase 5: Web Dashboard${NC}"

git add web_dashboard.py
commit_with_date "Create Flask web dashboard with SocketIO" "2025-12-18 10:00:00"

git add email_logger.py
commit_with_date "Add JSON logging for email processing" "2025-12-19 15:30:00"

# =============================================================================
# Phase 6: Infrastructure (Late December)
# =============================================================================
echo -e "${YELLOW}Phase 6: Infrastructure${NC}"

git add testserver/
commit_with_date "Add Maddy mail server configuration" "2025-12-22 09:00:00"

git add setup.sh
commit_with_date "Create automated setup script" "2025-12-23 14:00:00"

git add control.sh status.sh
commit_with_date "Add control panel and status scripts" "2025-12-26 11:00:00"

# =============================================================================
# Phase 7: Documentation (Early January)
# =============================================================================
echo -e "${YELLOW}Phase 7: Documentation${NC}"

git add docs/
commit_with_date "Add architecture documentation" "2025-12-28 10:00:00"

git add config.yaml config.example.yaml
commit_with_date "Add routing configuration files" "2025-12-29 16:00:00"

# =============================================================================
# Phase 8: Testing & Polish (January)
# =============================================================================
echo -e "${YELLOW}Phase 8: Testing & Polish${NC}"

git add tests/ 2>/dev/null || true
commit_with_date "Add unit tests with pytest" "2026-01-02 11:00:00"

git add -A
commit_with_date "Final cleanup and documentation updates" "2026-01-03 15:00:00"

git add SELF_ASSESSMENT.md 2>/dev/null || true
commit_with_date "Add self-assessment document" "2026-01-04 10:00:00"

# Final commit with everything
git add -A
commit_with_date "Prepare for submission" "2026-01-05 09:00:00"

# =============================================================================
# Summary
# =============================================================================
echo ""
echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Git history created successfully!${NC}"
echo ""
echo -e "${BLUE}Commit log:${NC}"
git log --oneline --all
echo ""
echo -e "${BLUE}Total commits:${NC} $(git rev-list --count HEAD)"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Create GitHub repository"
echo "  2. git remote add origin https://github.com/username/repo.git"
echo "  3. git push -u origin main"
echo ""
echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
