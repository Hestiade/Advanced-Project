"""IMAP client for fetching emails."""

import email
from email.header import decode_header
from typing import Optional, Iterator

from imapclient import IMAPClient as IMAPLib

from .models import Email


class IMAPClient:
    """IMAP email fetcher."""
    
    def __init__(self, host: str, port: int, address: str, password: str, 
                 use_ssl: bool = True, use_starttls: bool = False):
        self.host = host
        self.port = port
        self.address = address
        self.password = password
        self.use_ssl = use_ssl
        self.use_starttls = use_starttls
        self._client: Optional[IMAPLib] = None
    
    def connect(self) -> None:
        """Connect to IMAP server."""
        # Connect to IMAP server - standard initialization
        self._client = IMAPLib(self.host, port=self.port, ssl=self.use_ssl)
        
        # Use STARTTLS if enabled and not using SSL
        if self.use_starttls and not self.use_ssl:
            # Global SSL patch will handle verification if needed
            self._client.starttls()
        
        self._client.login(self.address, self.password)
        self._client.select_folder("INBOX")
    
    def disconnect(self) -> None:
        """Disconnect from IMAP server."""
        if self._client:
            try:
                self._client.logout()
            except Exception:
                pass
            self._client = None
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
    
    def fetch_unread(self) -> Iterator[Email]:
        """Fetch all unread emails."""
        if not self._client:
            raise RuntimeError("Not connected to IMAP server")
        
        uids = self._client.search(["UNSEEN"])
        
        if not uids:
            return
        
        for uid, data in self._client.fetch(uids, ["RFC822"]).items():
            raw = data[b"RFC822"]
            msg = email.message_from_bytes(raw)
            
            yield Email(
                uid=uid,
                from_addr=self._decode_header(msg.get("From", "")),
                to_addr=self._decode_header(msg.get("To", "")),
                subject=self._decode_header(msg.get("Subject", "")),
                body=self._get_body(msg),
                date=msg.get("Date", ""),
                raw=raw,
            )
    
    def fetch_from_folder(self, folder: str) -> list[Email]:
        """Fetch all emails from a specific folder."""
        if not self._client:
            raise RuntimeError("Not connected to IMAP server")
        
        # Check if folder exists
        if not self._client.folder_exists(folder):
            return []
        
        results = []
        try:
            self._client.select_folder(folder)
            uids = self._client.search(["ALL"])
            
            if not uids:
                return []
            
            for uid, data in self._client.fetch(uids, ["RFC822"]).items():
                raw = data[b"RFC822"]
                msg = email.message_from_bytes(raw)
                
                results.append(Email(
                    uid=uid,
                    from_addr=self._decode_header(msg.get("From", "")),
                    to_addr=self._decode_header(msg.get("To", "")),
                    subject=self._decode_header(msg.get("Subject", "")),
                    body=self._get_body(msg),
                    date=msg.get("Date", ""),
                    raw=raw,
                ))
        finally:
            # Always switch back to INBOX
            self._client.select_folder("INBOX")
        
        return results
    
    def mark_as_read(self, uid: int) -> None:
        """Mark email as read."""
        if not self._client:
            raise RuntimeError("Not connected to IMAP server")
        self._client.add_flags([uid], ["\\Seen"])
    
    def flag_email(self, uid: int, flag: str = "\\Flagged") -> None:
        """Add a flag to an email (e.g. \\Flagged for starring)."""
        if not self._client:
            raise RuntimeError("Not connected to IMAP server")
        self._client.add_flags([uid], [flag])

    def move_email(self, uid: int, folder: str, source_folder: str = "INBOX") -> None:
        """Move email to a specific folder from source folder."""
        if not self._client:
            raise RuntimeError("Not connected to IMAP server")
        
        # Select source folder to find the email
        self._client.select_folder(source_folder)
        
        # Ensure destination folder exists
        if not self._client.folder_exists(folder):
            self._client.create_folder(folder)
            
        self._client.move([uid], folder)
        
        # Switch back to INBOX for subsequent operations
        self._client.select_folder("INBOX")
    
    def _decode_header(self, header: str) -> str:
        """Decode email header."""
        if not header:
            return ""
        
        decoded_parts = []
        for part, encoding in decode_header(header):
            if isinstance(part, bytes):
                decoded_parts.append(
                    part.decode(encoding or "utf-8", errors="replace")
                )
            else:
                decoded_parts.append(part)
        
        return " ".join(decoded_parts)
    
    def _get_body(self, msg: email.message.Message) -> str:
        """Extract email body text."""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        return payload.decode(charset, errors="replace")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
        
        return ""
