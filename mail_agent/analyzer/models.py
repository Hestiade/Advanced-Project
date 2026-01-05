"""Analysis result models."""

from dataclasses import dataclass, field


@dataclass
class AnalysisResult:
    """Result from AI email analysis."""
    forward_to: str  # Primary destination
    category: str
    confidence: float
    reasoning: str
    additional_destinations: list[str] = field(default_factory=list)  # For multi-category emails
