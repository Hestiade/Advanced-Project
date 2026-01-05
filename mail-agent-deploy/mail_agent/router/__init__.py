"""AI Mail Redirection Agent - Router package."""

from .engine import Router
from .models import Rule, RoutingDecision

__all__ = ["Router", "Rule", "RoutingDecision"]
