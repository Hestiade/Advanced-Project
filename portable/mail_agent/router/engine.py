"""Email routing engine."""

from typing import Optional, Union

from ..analyzer import GeminiAnalyzer, OllamaAnalyzer
from ..client import Email
from .models import Rule, RoutingDecision


class Router:
    """Email routing decision engine."""
    
    def __init__(
        self, 
        rules: list[Rule], 
        ai_enabled: bool = False,
        gemini_api_key: str = "",
        ollama_model: str = "",
        ai_destinations: list[dict] = None,
        default_action: str = "analyze",
        company_name: str = "TechCorp Industries",
        company_mailbox: str = "company@mail.local"
    ):
        self.rules = rules
        self.default_action = default_action
        self._analyzer: Optional[Union[GeminiAnalyzer, OllamaAnalyzer]] = None
        
        # Prefer Ollama if configured, fall back to Gemini
        if ai_enabled:
            if ollama_model:
                self._analyzer = OllamaAnalyzer(
                    ollama_model, 
                    ai_destinations or [],
                    company_name=company_name,
                    company_mailbox=company_mailbox
                )
            elif gemini_api_key:
                self._analyzer = GeminiAnalyzer(gemini_api_key, ai_destinations or [])
    
    def decide(self, email: Email) -> RoutingDecision:
        """Decide where to route an email."""
        email_data = email.to_dict()
        
        # Check rules first
        for rule in self.rules:
            if rule.matches(email_data):
                return RoutingDecision(
                    forward_to=rule.forward_to,
                    matched_rule=rule.name,
                    ai_result=None,
                    should_forward=bool(rule.forward_to),
                    additional_destinations=[],
                )
        
        # Fall back to AI if enabled
        if self._analyzer and self.default_action in ("analyze", "ai_route"):
            ai_result = self._analyzer.analyze(email_data)
            return RoutingDecision(
                forward_to=ai_result.forward_to,
                matched_rule=None,
                ai_result=ai_result,
                should_forward=bool(ai_result.forward_to) and ai_result.confidence >= 0.7,
                additional_destinations=ai_result.additional_destinations,
            )
        
        # No routing
        return RoutingDecision(
            forward_to="",
            matched_rule=None,
            ai_result=None,
            should_forward=False,
            additional_destinations=[],
        )
