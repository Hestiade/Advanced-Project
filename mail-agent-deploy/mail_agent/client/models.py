"""Email data models."""

from dataclasses import dataclass


@dataclass
class Email:
    """Parsed email data."""
    uid: int
    from_addr: str
    to_addr: str
    subject: str
    body: str
    date: str
    raw: bytes
    
    def to_dict(self) -> dict:
        """Convert to dictionary for rule matching."""
        return {
            "from": self.from_addr,
            "to": self.to_addr,
            "subject": self.subject,
            "body": self.body,
            "date": self.date,
        }
