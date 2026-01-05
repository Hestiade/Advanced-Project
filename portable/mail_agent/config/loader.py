"""Configuration loader."""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

from .models import Config, EmailConfig, AIRoutingConfig, CompanyConfig
from ..router.models import Rule


def load_config(config_path: str = "config.yaml") -> Config:
    """Load configuration from YAML file and environment."""
    load_dotenv()
    
    # Load email config from environment
    email_config = EmailConfig(
        imap_host=os.getenv("IMAP_HOST", "imap.gmail.com"),
        imap_port=int(os.getenv("IMAP_PORT", "993")),
        smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        address=os.getenv("EMAIL_ADDRESS", ""),
        password=os.getenv("EMAIL_PASSWORD", ""),
        use_ssl=os.getenv("IMAP_USE_SSL", "true").lower() == "true",
        use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
        use_starttls=os.getenv("IMAP_USE_STARTTLS", "false").lower() == "true",
    )
    
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    ollama_model = os.getenv("OLLAMA_MODEL", "")
    
    # Load rules from YAML
    rules = []
    ai_routing = AIRoutingConfig()
    default_action = "analyze"
    
    config_file = Path(config_path)
    if config_file.exists():
        with open(config_file) as f:
            yaml_config = yaml.safe_load(f) or {}
        
        default_action = yaml_config.get("default_action", "analyze")
        
        for rule_data in yaml_config.get("rules", []):
            match = rule_data.get("match", {})
            action = rule_data.get("action", {})
            rules.append(Rule(
                name=rule_data.get("name", "Unnamed"),
                match_from=match.get("from"),
                match_subject=match.get("subject"),
                match_keywords=match.get("keywords"),
                forward_to=action.get("forward_to", ""),
            ))
        
        ai_data = yaml_config.get("ai_routing", {})
        ai_routing = AIRoutingConfig(
            enabled=ai_data.get("enabled", True),
            destinations=ai_data.get("destinations", []),
        )
        
        # Parse company identity from YAML
        company_data = yaml_config.get("company", {})
        company = CompanyConfig(
            name=company_data.get("name", "TechCorp Industries"),
            domain=company_data.get("domain", "techcorp.com"),
            mailbox=company_data.get("mailbox", "company@mail.local"),
            description=company_data.get("description", ""),
        )
    else:
        company = CompanyConfig()
    
    return Config(
        email=email_config,
        rules=rules,
        ai_routing=ai_routing,
        company=company,
        default_action=default_action,
        gemini_api_key=gemini_key,
        ollama_model=ollama_model,
    )

