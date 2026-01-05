"""Configuration models."""

from dataclasses import dataclass, field


@dataclass
class EmailConfig:
    """Email server configuration."""
    imap_host: str
    imap_port: int
    smtp_host: str
    smtp_port: int
    address: str
    password: str
    use_ssl: bool = True
    use_tls: bool = True
    use_starttls: bool = False


@dataclass
class AIRoutingConfig:
    """AI routing configuration."""
    enabled: bool = True
    destinations: list[dict] = field(default_factory=list)


@dataclass
class CompanyConfig:
    """Company identity configuration (used in LLM prompt)."""
    name: str = "TechCorp Industries"
    domain: str = "techcorp.com"
    mailbox: str = "company@mail.local"
    description: str = ""


@dataclass
class Config:
    """Main configuration container."""
    email: EmailConfig
    rules: list  # List of Rule objects from router
    ai_routing: AIRoutingConfig
    company: CompanyConfig = field(default_factory=CompanyConfig)
    default_action: str = "analyze"
    gemini_api_key: str = ""
    ollama_model: str = ""
