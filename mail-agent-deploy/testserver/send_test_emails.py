import smtplib
import os
import glob
from email.message import EmailMessage
from pathlib import Path

# Load .env file
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

# Configuration from .env
SMTP_SERVER = os.getenv('SMTP_HOST', 'localhost')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
USE_TLS = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
SENDER_EMAIL = os.getenv('TEST_SENDER_EMAIL', 'deniz@mail.local')
SENDER_PASSWORD = os.getenv('TEST_SENDER_PASSWORD', 'deniz01')
RECIPIENT_EMAIL = os.getenv('EMAIL_ADDRESS', 'company@mail.local')
SAMPLES_DIR = Path(__file__).parent / "samples"

def send_emails():
    # Find all sample files
    files = sorted(glob.glob(os.path.join(SAMPLES_DIR, "email_*.txt")))
    
    if not files:
        print(f"No email sample files found in {SAMPLES_DIR}")
        return

    print(f"Found {len(files)} test emails to send.")
    print(f"From: {SENDER_EMAIL} → To: {RECIPIENT_EMAIL}")
    print(f"Server: {SMTP_SERVER}:{SMTP_PORT} (TLS: {USE_TLS})")

    try:
        # Connect to SMTP server
        print(f"Connecting to SMTP server...")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            if USE_TLS:
                server.starttls() 
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            print("Login successful.")

            for file_path in files:
                filename = os.path.basename(file_path)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                
                # Parse Subject and Body
                lines = content.split('\n')
                subject_line = lines[0]
                
                if subject_line.lower().startswith("subject:"):
                    subject = subject_line[8:].strip()
                else:
                    # Fallback if format is slightly off
                    subject = f"Test Email from {filename}"
                
                # Body is everything after the first line
                body = "\n".join(lines[1:]).strip()

                msg = EmailMessage()
                msg.set_content(body)
                msg['Subject'] = subject
                msg['From'] = SENDER_EMAIL
                msg['To'] = RECIPIENT_EMAIL

                try:
                    server.send_message(msg)
                    print(f"Sent: {filename} - '{subject}'")
                except Exception as e:
                    print(f"Failed to send {filename}: {e}")

    except Exception as e:
        print(f"SMTP Error: {e}")

if __name__ == "__main__":
    send_emails()
