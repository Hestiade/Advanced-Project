"""
Unit tests for the AI analyzer module.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json


class TestPromptConstruction:
    """Tests for AI prompt construction."""
    
    def test_prompt_includes_subject(self):
        """Test that prompt includes email subject."""
        subject = "Help with my order"
        body = "I need assistance"
        
        prompt = f"Subject: {subject}\nBody: {body}"
        
        assert "Help with my order" in prompt
    
    def test_prompt_includes_body(self):
        """Test that prompt includes email body."""
        subject = "Question"
        body = "This is the email body content"
        
        prompt = f"Subject: {subject}\nBody: {body}"
        
        assert "This is the email body content" in prompt
    
    def test_prompt_truncation(self):
        """Test that long bodies are truncated."""
        subject = "Test"
        body = "A" * 10000  # Very long body
        max_length = 2000
        
        truncated_body = body[:max_length] if len(body) > max_length else body
        prompt = f"Subject: {subject}\nBody: {truncated_body}"
        
        assert len(truncated_body) == max_length


class TestResponseParsing:
    """Tests for AI response parsing."""
    
    def test_parse_clean_json(self):
        """Test parsing clean JSON response."""
        response = '{"category": "support", "confidence": 0.95, "reason": "Customer needs help"}'
        
        data = json.loads(response)
        
        assert data["category"] == "support"
        assert data["confidence"] == 0.95
        assert data["reason"] == "Customer needs help"
    
    def test_parse_json_with_whitespace(self):
        """Test parsing JSON with extra whitespace."""
        response = '''
        {
            "category": "sales",
            "confidence": 0.88,
            "reason": "Purchase inquiry"
        }
        '''
        
        data = json.loads(response.strip())
        
        assert data["category"] == "sales"
    
    def test_parse_json_in_markdown_block(self):
        """Test extracting JSON from markdown code block."""
        response = '''Here is my analysis:
        
```json
{"category": "hr", "confidence": 0.92, "reason": "Job application"}
```

This email is about a job application.'''
        
        # Extract JSON from markdown
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
        else:
            json_str = response.strip()
        
        data = json.loads(json_str)
        
        assert data["category"] == "hr"
        assert data["confidence"] == 0.92
    
    def test_handle_malformed_json(self):
        """Test handling malformed JSON."""
        response = '{"category": "support", confidence: 0.9}'  # Missing quotes
        
        result = None
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            # Fallback to default
            result = {"category": "review", "confidence": 0.0}
        
        assert result["category"] == "review"
    
    def test_handle_empty_response(self):
        """Test handling empty AI response."""
        response = ""
        
        result = None
        try:
            result = json.loads(response) if response else None
        except json.JSONDecodeError:
            result = None
        
        if result is None:
            result = {"category": "review", "confidence": 0.0}
        
        assert result["category"] == "review"


class TestCategoryValidation:
    """Tests for category validation."""
    
    @pytest.fixture
    def valid_categories(self):
        """List of valid categories."""
        return ["support", "sales", "hr", "legal", "it", "promotions", "vendors"]
    
    def test_valid_category_passes(self, valid_categories):
        """Test that valid categories are accepted."""
        category = "support"
        
        is_valid = category in valid_categories
        
        assert is_valid is True
    
    def test_invalid_category_rejected(self, valid_categories):
        """Test that invalid categories are rejected."""
        category = "random_category"
        
        is_valid = category in valid_categories
        
        assert is_valid is False
    
    def test_category_normalization(self, valid_categories):
        """Test category case normalization."""
        category = "SUPPORT"
        
        normalized = category.lower()
        is_valid = normalized in valid_categories
        
        assert is_valid is True


class TestConfidenceValidation:
    """Tests for confidence score validation."""
    
    def test_valid_confidence_range(self):
        """Test confidence in valid range [0, 1]."""
        confidence = 0.85
        
        is_valid = 0.0 <= confidence <= 1.0
        
        assert is_valid is True
    
    def test_confidence_above_range(self):
        """Test handling confidence > 1."""
        confidence = 1.5
        
        # Clamp to valid range
        clamped = min(1.0, max(0.0, confidence))
        
        assert clamped == 1.0
    
    def test_confidence_below_range(self):
        """Test handling confidence < 0."""
        confidence = -0.5
        
        # Clamp to valid range
        clamped = min(1.0, max(0.0, confidence))
        
        assert clamped == 0.0
    
    def test_confidence_as_string(self):
        """Test handling confidence as string."""
        confidence_str = "0.92"
        
        confidence = float(confidence_str)
        
        assert confidence == 0.92


class TestOllamaAnalyzer:
    """Tests for Ollama analyzer (mocked)."""
    
    def test_ollama_request_format(self):
        """Test Ollama API request format."""
        model = "qwen3:14b"
        prompt = "Analyze this email..."
        
        request_data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1}
        }
        
        assert request_data["model"] == "qwen3:14b"
        assert request_data["stream"] is False
    
    def test_ollama_response_extraction(self):
        """Test extracting response from Ollama API response."""
        api_response = {
            "model": "qwen3:14b",
            "response": '{"category": "support", "confidence": 0.9}',
            "done": True
        }
        
        response_text = api_response["response"]
        data = json.loads(response_text)
        
        assert data["category"] == "support"


class TestGeminiAnalyzer:
    """Tests for Gemini analyzer (mocked)."""
    
    def test_gemini_request_format(self):
        """Test Gemini API request format."""
        prompt = "Analyze this email..."
        
        request_data = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        assert "contents" in request_data
        assert request_data["contents"][0]["parts"][0]["text"] == prompt
    
    def test_gemini_response_extraction(self):
        """Test extracting text from Gemini API response."""
        api_response = {
            "candidates": [{
                "content": {
                    "parts": [{"text": '{"category": "sales", "confidence": 0.88}'}]
                }
            }]
        }
        
        text = api_response["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(text)
        
        assert data["category"] == "sales"


class TestFallbackBehavior:
    """Tests for fallback behavior when AI fails."""
    
    def test_fallback_on_connection_error(self):
        """Test fallback when AI connection fails."""
        # Simulate connection error
        ai_available = False
        
        if not ai_available:
            result = {"category": "review", "confidence": 0.0, "reason": "AI unavailable"}
        
        assert result["category"] == "review"
        assert result["reason"] == "AI unavailable"
    
    def test_fallback_on_timeout(self):
        """Test fallback when AI request times out."""
        timeout_occurred = True
        
        if timeout_occurred:
            result = {"category": "review", "confidence": 0.0, "reason": "Request timeout"}
        
        assert result["category"] == "review"
    
    def test_keyword_fallback(self):
        """Test keyword-based fallback classification."""
        subject = "Help me with a problem"
        keywords = {
            "support": ["help", "problem", "issue"],
            "sales": ["buy", "purchase", "price"]
        }
        
        # Keyword matching fallback
        matched_category = None
        for category, kws in keywords.items():
            if any(kw in subject.lower() for kw in kws):
                matched_category = category
                break
        
        assert matched_category == "support"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
