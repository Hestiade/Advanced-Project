"""AI Mail Redirection Agent - Analyzer package."""

from .gemini import GeminiAnalyzer
from .ollama import OllamaAnalyzer
from .models import AnalysisResult

__all__ = ["GeminiAnalyzer", "OllamaAnalyzer", "AnalysisResult"]
