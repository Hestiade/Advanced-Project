"""Gemini-powered email analyzer using the new google-genai SDK."""

from google import genai
from google.genai import types

from .models import AnalysisResult


class GeminiAnalyzer:
    """Gemini AI email content analyzer."""
    
    def __init__(self, api_key: str, destinations: list[dict]):
        self.destinations = destinations
        self.client = genai.Client(api_key=api_key)
    
    def analyze(self, email_data: dict) -> AnalysisResult:
        """Analyze email and determine routing destination."""
        if not self.destinations:
            return AnalysisResult(
                forward_to="",
                category="unknown",
                confidence=0.0,
                reasoning="No destinations configured for AI routing",
            )
        
        destinations_text = "\n".join(
            f"- {d['email']}: {d['description']}"
            for d in self.destinations
        )
        
        prompt = f"""Analyze this email and determine which destination address it should be forwarded to.

EMAIL DETAILS:
From: {email_data.get('from', 'Unknown')}
Subject: {email_data.get('subject', 'No subject')}
Body:
{email_data.get('body', '')[:2000]}

AVAILABLE DESTINATIONS:
{destinations_text}

Respond in EXACTLY this format (no markdown, just plain text):
FORWARD_TO: <email address from the list above>
CATEGORY: <one word category like: personal, work, newsletter, spam, urgent, social>
CONFIDENCE: <number between 0.0 and 1.0>
REASONING: <brief one-line explanation>
"""
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=prompt,
            )
            return self._parse_response(response.text)
        except Exception as e:
            return AnalysisResult(
                forward_to="",
                category="error",
                confidence=0.0,
                reasoning=f"AI analysis failed: {str(e)}",
            )
    
    def _parse_response(self, response: str) -> AnalysisResult:
        """Parse the AI response into structured result."""
        lines = response.strip().split("\n")
        
        forward_to = ""
        category = "unknown"
        confidence = 0.5
        reasoning = ""
        
        for line in lines:
            line = line.strip()
            if line.startswith("FORWARD_TO:"):
                forward_to = line.split(":", 1)[1].strip()
            elif line.startswith("CATEGORY:"):
                category = line.split(":", 1)[1].strip().lower()
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = float(line.split(":", 1)[1].strip())
                except ValueError:
                    confidence = 0.5
            elif line.startswith("REASONING:"):
                reasoning = line.split(":", 1)[1].strip()
        
        return AnalysisResult(
            forward_to=forward_to,
            category=category,
            confidence=confidence,
            reasoning=reasoning,
        )
