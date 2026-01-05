#!/usr/bin/env python3
"""Clear all emails from all Maddy mail server accounts, including processed folders."""

import imaplib
import os
from pathlib import Path

# Load .env file
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

ACCOUNTS = [
    ('company@mail.local', 'company01'),
    ('support@mail.local', 'support01'),
    ('sales@mail.local', 'sales01'),
    ('vendors@mail.local', 'vendors01'),
    ('hr@mail.local', 'hr01'),
    ('it@mail.local', 'it01'),
    ('legal@mail.local', 'legal01'),
    ('spam@mail.local', 'spam01'),
    ('promotions@mail.local', 'promotions01'),
]

# Folders created by the web dashboard
FOLDERS_TO_CLEAR = ['INBOX', 'Processed', 'Review', 'Skipped', 'Quarantine']

# Read from environment
IMAP_HOST = os.getenv('IMAP_HOST', 'localhost')
IMAP_PORT = int(os.getenv('IMAP_PORT', '143'))
USE_SSL = os.getenv('IMAP_USE_SSL', 'false').lower() == 'true'
USE_STARTTLS = os.getenv('IMAP_USE_STARTTLS', 'true').lower() == 'true'


def clear_folder(imap: imaplib.IMAP4, folder: str) -> int:
    """Clear all emails from a specific folder. Returns count deleted."""
    try:
        status, _ = imap.select(folder)
        if status != 'OK':
            return 0
        
        status, messages = imap.search(None, 'ALL')
        count = 0
        
        if messages[0]:
            for num in messages[0].split():
                imap.store(num, '+FLAGS', '\\Deleted')
                count += 1
            imap.expunge()
        
        return count
    except Exception:
        return 0


def clear_mailbox(email: str, password: str) -> tuple[str, dict]:
    """Clear all emails from a mailbox including all folders. Returns (status, folder_counts)."""
    try:
        # Connect with SSL or plain
        if USE_SSL:
            imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        else:
            imap = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
            # Use STARTTLS if enabled
            if USE_STARTTLS:
                try:
                    imap.starttls()
                except:
                    pass  # Server might not support STARTTLS
        
        imap.login(email, password)
        
        folder_counts = {}
        
        for folder in FOLDERS_TO_CLEAR:
            count = clear_folder(imap, folder)
            if count > 0:
                folder_counts[folder] = count
        
        imap.logout()
        return ('cleared', folder_counts)
    except Exception as e:
        return ('error', str(e))


def main():
    print("\n" + "="*60)
    print("  Clear All Mailboxes (including Processed/Review folders)")
    print("="*60 + "\n")
    
    total_cleared = 0
    
    for email, password in ACCOUNTS:
        status, result = clear_mailbox(email, password)
        
        if status == 'cleared':
            if result:
                account_total = sum(result.values())
                folders_str = ", ".join(f"{f}:{c}" for f, c in result.items())
                print(f"  ✓ {email}: {account_total} deleted ({folders_str})")
                total_cleared += account_total
            else:
                print(f"  ○ {email}: empty")
        else:
            print(f"  ✗ {email}: {result}")
    
    print("\n" + "-"*60)
    print(f"  Total cleared: {total_cleared} emails")
    print(f"  Folders checked: {', '.join(FOLDERS_TO_CLEAR)}")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
