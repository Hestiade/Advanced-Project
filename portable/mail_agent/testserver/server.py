"""Local test mail server for development and testing.

This module provides a simple IMAP/SMTP test server that stores emails in memory.
Useful for testing the mail agent without connecting to a real mail server.
"""

import asyncio
import email
import threading
import time
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from typing import Optional
import socket


@dataclass
class StoredEmail:
    """Email stored in the test server."""
    uid: int
    raw: bytes
    flags: set = field(default_factory=set)


class TestMailServer:
    """Simple in-memory test mail server with IMAP and SMTP support.
    
    This is a minimal implementation for testing purposes.
    It stores all emails in memory and provides basic IMAP/SMTP interfaces.
    """
    
    def __init__(self, imap_port: int = 10143, smtp_port: int = 10025):
        self.imap_port = imap_port
        self.smtp_port = smtp_port
        self.emails: list[StoredEmail] = []
        self.uid_counter = 1
        self._running = False
        self._imap_server: Optional[socket.socket] = None
        self._smtp_server: Optional[socket.socket] = None
        self._threads: list[threading.Thread] = []
    
    def add_test_email(
        self, 
        from_addr: str, 
        to_addr: str, 
        subject: str, 
        body: str
    ) -> int:
        """Add a test email to the inbox. Returns the UID."""
        msg = MIMEText(body)
        msg["From"] = from_addr
        msg["To"] = to_addr
        msg["Subject"] = subject
        msg["Date"] = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())
        
        stored = StoredEmail(
            uid=self.uid_counter,
            raw=msg.as_bytes(),
        )
        self.emails.append(stored)
        self.uid_counter += 1
        return stored.uid
    
    def get_email(self, uid: int) -> Optional[StoredEmail]:
        """Get an email by UID."""
        for email in self.emails:
            if email.uid == uid:
                return email
        return None
    
    def mark_as_read(self, uid: int) -> bool:
        """Mark an email as read."""
        email = self.get_email(uid)
        if email:
            email.flags.add("\\Seen")
            return True
        return False
    
    def get_unread(self) -> list[StoredEmail]:
        """Get all unread emails."""
        return [e for e in self.emails if "\\Seen" not in e.flags]
    
    def clear(self) -> None:
        """Clear all emails."""
        self.emails.clear()
        self.uid_counter = 1
    
    def start(self) -> None:
        """Start the test server (SMTP only for sending test emails).
        
        Note: This is a simplified server. For full IMAP testing, 
        use the mock client provided in this module instead.
        """
        self._running = True
        print(f"Test mail server started")
        print(f"  - Use add_test_email() to inject test emails")
        print(f"  - Use TestIMAPClient for IMAP operations")
    
    def stop(self) -> None:
        """Stop the test server."""
        self._running = False
        print("Test mail server stopped")


class TestIMAPClient:
    """Mock IMAP client that works with TestMailServer.
    
    Use this instead of the real IMAPClient when testing.
    """
    
    def __init__(self, server: TestMailServer):
        self.server = server
        self._connected = False
    
    def connect(self) -> None:
        """Connect to the test server."""
        self._connected = True
    
    def disconnect(self) -> None:
        """Disconnect from the test server."""
        self._connected = False
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
    
    def fetch_unread(self):
        """Fetch all unread emails."""
        if not self._connected:
            raise RuntimeError("Not connected")
        
        from ..client import Email
        
        for stored in self.server.get_unread():
            msg = email.message_from_bytes(stored.raw)
            
            yield Email(
                uid=stored.uid,
                from_addr=msg.get("From", ""),
                to_addr=msg.get("To", ""),
                subject=msg.get("Subject", ""),
                body=self._get_body(msg),
                date=msg.get("Date", ""),
                raw=stored.raw,
            )
    
    def mark_as_read(self, uid: int) -> None:
        """Mark email as read."""
        if not self._connected:
            raise RuntimeError("Not connected")
        self.server.mark_as_read(uid)
    
    def _get_body(self, msg) -> str:
        """Extract email body."""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        return payload.decode("utf-8", errors="replace")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                return payload.decode("utf-8", errors="replace")
        return ""


class TestSMTPClient:
    """Mock SMTP client that captures sent emails.
    
    Use this instead of the real SMTPClient when testing.
    """
    
    def __init__(self):
        self.sent_emails: list[dict] = []
    
    def forward_email(self, original, to_addr: str) -> None:
        """Capture forwarded email instead of actually sending."""
        self.sent_emails.append({
            "original_from": original.from_addr,
            "original_subject": original.subject,
            "forwarded_to": to_addr,
        })
    
    def clear(self) -> None:
        """Clear sent emails."""
        self.sent_emails.clear()
