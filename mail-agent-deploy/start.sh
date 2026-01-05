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
