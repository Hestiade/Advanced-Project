# MBP Server Files

Scripts to run on your MacBook Pro M3 for Ollama + battery monitoring.

## Setup

1. Copy this folder to your Mac
2. Make sure Python 3 is installed
3. Run:
   ```bash
   python3 mac_control.py
   ```

## Files

- `mac_control.py` - Interactive control panel + API server

## API Endpoints

When running with `--serve`, the following endpoints are available on port `11435`:

| Endpoint | Description |
|----------|-------------|
| `/status` | Full system status (battery + Ollama) |
| `/battery` | Battery percentage and charging status |
| `/ollama` | Ollama running status and loaded models |

## Usage

### Interactive Mode
```bash
python3 mac_control.py
```

### API Server Mode (for remote monitoring)
```bash
python3 mac_control.py --serve
```

This runs the API server in foreground on port 11435.

## Example API Response

```json
{
  "hostname": "Deniz-MBP",
  "battery": {
    "percentage": 85,
    "status": "charging",
    "time_remaining": null
  },
  "ollama": {
    "running": true,
    "models": ["qwen2.5:14b"]
  },
  "timestamp": "2025-12-27 05:10:00"
}
```
