"""AI Mail Redirection Agent - Intelligent email routing powered by Gemini."""

__version__ = "0.1.0"

# Re-export main components for convenience
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
