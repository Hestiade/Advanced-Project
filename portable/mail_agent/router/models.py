"""Router models - rules and decisions."""

from dataclasses import dataclass
from typing import Optional

from ..analyzer.models import AnalysisResult


@dataclass
class Rule:
    """A single redirect rule."""
    name: str
    match_from: Optional[str] = None
    match_subject: Optional[list[str]] = None
    match_keywords: Optional[list[str]] = None
    forward_to: str = ""
    
    def matches(self, email_data: dict) -> bool:
        """Check if email matches this rule."""
        if self.match_from:
            sender = email_data.get("from", "").lower()
            pattern = self.match_from.replace("*", "").lower()
            if pattern not in sender:
                return False
        
        if self.match_subject:
            subject = email_data.get("subject", "").lower()
            if not any(kw.lower() in subject for kw in self.match_subject):
                return False
        
        if self.match_keywords:
            body = email_data.get("body", "").lower()
            subject = email_data.get("subject", "").lower()
            text = f"{subject} {body}"
            if not any(kw.lower() in text for kw in self.match_keywords):
                return False
        
        return True


@dataclass
class RoutingDecision:
    """Routing decision for an email."""
    forward_to: str
    matched_rule: Optional[str]
    ai_result: Optional[AnalysisResult]
    should_forward: bool
    additional_destinations: list[str] = None
    
    def __post_init__(self):
        if self.additional_destinations is None:
            self.additional_destinations = []
    
    @property
    def all_destinations(self) -> list[str]:
        """Return all destinations including primary and additional."""
        destinations = [self.forward_to] if self.forward_to else []
        destinations.extend(self.additional_destinations or [])
        return destinations
    
    @property
    def source(self) -> str:
        """Return where the decision came from."""
        if self.matched_rule:
            return f"Rule: {self.matched_rule}"
        elif self.ai_result:
            return f"AI ({self.ai_result.category}, {self.ai_result.confidence:.0%} confident)"
        return "No match"

