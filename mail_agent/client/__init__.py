"""AI Mail Redirection Agent - Email client package."""

from .imap_client import IMAPClient
from .smtp_client import SMTPClient
from .models import Email

__all__ = ["IMAPClient", "SMTPClient", "Email"]
