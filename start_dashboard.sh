#!/bin/bash
# Start the AI Mail Redirection Agent Web Dashboard

cd "$(dirname "${BASH_SOURCE[0]}")"

# Load .env file
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Kill any existing instance
pkill -f "python.*web_dashboard" 2>/dev/null
sleep 1

# Activate virtual environment
source .venv/bin/activate

echo ""
echo "=================================================="
echo "  AI Mail Redirection Agent - Web Dashboard"
echo "=================================================="
echo ""
echo "  Open in browser: http://localhost:5000"
echo "  Press Ctrl+C to stop"
echo ""
echo "=================================================="
echo ""

# Run the dashboard (blocks terminal)
python web_dashboard.py
