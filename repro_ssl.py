from mail_agent.client.imap_client import IMAPClient
from mail_agent.config.loader import load_config
import logging

logging.basicConfig(level=logging.INFO)

try:
    print("Attempting connection...")
    # Initialize with local settings (using defaults from .env if present)
    client = IMAPClient(
        host='127.0.0.1',
        port=993,
        address='company@mail.local',
        password='company01',
        use_ssl=True
    )
    client.connect()
    print("SUCCESS: Connected!")
    client.disconnect()
except Exception as e:
    print(f"FAILED: {e}")
