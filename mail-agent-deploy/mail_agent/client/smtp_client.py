"""SMTP client for sending/forwarding emails."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from .models import Email


class SMTPClient:
    """SMTP email sender."""
    
    def __init__(self, host: str, port: int, address: str, password: str, use_tls: bool = True):
        self.host = host
        self.port = port
        self.address = address
        self.password = password
        self.use_tls = use_tls
    
    def forward_email(self, original: Email, to_addr: str) -> None:
        """Forward an email to a new address."""
        msg = MIMEMultipart()
        msg["From"] = self.address
        msg["To"] = to_addr
        msg["Subject"] = f"Fwd: {original.subject}"
        
        forward_body = f"""
---------- Forwarded message ----------
From: {original.from_addr}
Date: {original.date}
Subject: {original.subject}
To: {original.to_addr}

{original.body}
"""
        msg.attach(MIMEText(forward_body, "plain"))
        
        with smtplib.SMTP(self.host, self.port) as smtp:
            if self.use_tls:
                smtp.starttls()
            smtp.login(self.address, self.password)
            smtp.send_message(msg)
