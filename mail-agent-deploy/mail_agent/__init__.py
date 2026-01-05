"""AI Mail Redirection Agent - Intelligent email routing powered by Gemini."""

__version__ = "0.1.0"

# Re-export main components for convenience
import ssl

# GLOBAL SSL PATCH: Disable certificate verification for all modules.
# This is required to allow connection to the local connection with the
# self-signed 'maddy' certificate, without triggering imapclient bugs on Windows.
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context
    ssl.create_default_context = _create_unverified_https_context

from .config import load_config, Config
from .client import IMAPClient, SMTPClient, Email
from .analyzer import GeminiAnalyzer, AnalysisResult
from .router import Router, Rule, RoutingDecision

__all__ = [
    "load_config",
    "Config",
    "IMAPClient",
    "SMTPClient", 
    "Email",
    "GeminiAnalyzer",
    "AnalysisResult",
    "Router",
    "Rule",
    "RoutingDecision",
]
