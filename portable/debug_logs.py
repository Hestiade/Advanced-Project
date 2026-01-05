import json
from pathlib import Path
import sys

# Mocking the logic
try:
    log_dir = Path(__file__).parent / "logs"
    print(f"Log dir: {log_dir}")
    
    files = list(log_dir.glob("email_log_*.jsonl"))
    print(f"Found {len(files)} log files")
    
    if not files:
        sys.exit(0)
        
    latest = sorted(files)[-1]
    print(f"Reading {latest}")
    
    logs = []
    with open(latest) as f:
        for i, line in enumerate(f):
            if line.strip():
                try:
                    data = json.loads(line)
                    logs.append(data)
                except Exception as e:
                    print(f"Line {i} error: {e}")
    
    print(f"Loaded {len(logs)} entries")
    
    # Test serialization
    import flask
    from flask import json as flask_json
    
    try:
        serialized = flask_json.dumps(logs)
        print("Serialization OK")
    except Exception as e:
        print(f"Serialization Error: {e}")
        # Find which item fails
        for i, entry in enumerate(logs):
            try:
                flask_json.dumps(entry)
            except:
                print(f"Entry {i} failed serialization: {entry}")
                break

except Exception as e:
    print(f"General Error: {e}")
