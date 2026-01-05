"""AI Mail Redirection Agent - Configuration package."""

from .loader import load_config
from .models import Config, EmailConfig, AIRoutingConfig

__all__ = ["load_config", "Config", "EmailConfig", "AIRoutingConfig"]
