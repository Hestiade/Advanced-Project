# AI Mail Redirection Agent

Intelligent email routing powered by AI.

## Quick Setup (Windows)

1. **Extract the ZIP archive**.
2. **Double-click `start.bat`**.
   - First run will install Python dependencies automatically.
3. **Configure**: The script will create `.env`. Edit it with your mail settings.
4. **Dashboard**: The browser will open automatically.

## Quick Setup (Linux)

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
| `start.bat` | Windows launcher |

## Requirements

- Linux (Ubuntu/Debian)
- Python 3.10+
- Maddy Mail Server (installed by setup.sh)
- Ollama or Gemini API access
