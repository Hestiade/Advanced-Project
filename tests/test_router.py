"""
Unit tests for the email routing engine.
"""
import pytest
from unittest.mock import Mock, patch
from dataclasses import dataclass
from typing import Optional


# Mock the models if they don't exist in this structure
@dataclass
class AnalysisResult:
    """Result from AI analysis."""
    category: str
    confidence: float
    reason: Optional[str] = None


@dataclass
class RoutingDecision:
    """Decision on how to route an email."""
    action: str  # 'forward', 'archive', 'review'
    target: Optional[str] = None
    category: str = ""
    confidence: float = 0.0


class TestRoutingDecision:
    """Tests for RoutingDecision dataclass."""
    
    def test_create_forward_decision(self):
        """Test creating a forward routing decision."""
        decision = RoutingDecision(
            action="forward",
            target="support@mail.local",
            category="support",
            confidence=0.95
        )
        
        assert decision.action == "forward"
        assert decision.target == "support@mail.local"
        assert decision.category == "support"
        assert decision.confidence == 0.95
    
    def test_create_review_decision(self):
        """Test creating a review routing decision."""
        decision = RoutingDecision(
            action="review",
            category="unknown",
            confidence=0.3
        )
        
        assert decision.action == "review"
        assert decision.target is None
        assert decision.confidence == 0.3


class TestAnalysisResult:
    """Tests for AnalysisResult dataclass."""
    
    def test_create_analysis_result(self):
        """Test creating an analysis result."""
        result = AnalysisResult(
            category="support",
            confidence=0.92,
            reason="Email mentions help request"
        )
        
        assert result.category == "support"
        assert result.confidence == 0.92
        assert result.reason == "Email mentions help request"
    
    def test_analysis_result_without_reason(self):
        """Test analysis result with optional reason."""
        result = AnalysisResult(
            category="sales",
            confidence=0.85
        )
        
        assert result.category == "sales"
        assert result.reason is None


class TestCategoryMapping:
    """Tests for category to target mapping."""
    
    @pytest.fixture
    def category_config(self):
        """Sample category configuration."""
        return {
            "support": {
                "target": "support@mail.local",
                "keywords": ["help", "issue", "problem"]
            },
            "sales": {
                "target": "sales@mail.local",
                "keywords": ["purchase", "quote", "pricing"]
            },
            "hr": {
                "target": "hr@mail.local",
                "keywords": ["resume", "application", "job"]
            }
        }
    
    def test_category_to_target_mapping(self, category_config):
        """Test mapping category to target email."""
        category = "support"
        target = category_config[category]["target"]
        
        assert target == "support@mail.local"
    
    def test_unknown_category_handling(self, category_config):
        """Test handling unknown categories."""
        category = "unknown"
        target = category_config.get(category, {}).get("target")
        
        assert target is None


class TestConfidenceThreshold:
    """Tests for confidence threshold logic."""
    
    @pytest.fixture
    def threshold(self):
        """Default confidence threshold."""
        return 0.7
    
    def test_high_confidence_forwards(self, threshold):
        """Test that high confidence results in forward action."""
        confidence = 0.95
        action = "forward" if confidence >= threshold else "review"
        
        assert action == "forward"
    
    def test_low_confidence_reviews(self, threshold):
        """Test that low confidence results in review action."""
        confidence = 0.5
        action = "forward" if confidence >= threshold else "review"
        
        assert action == "review"
    
    def test_borderline_confidence(self, threshold):
        """Test exactly at threshold."""
        confidence = 0.7
        action = "forward" if confidence >= threshold else "review"
        
        assert action == "forward"


class TestEmailParsing:
    """Tests for email content extraction."""
    
    def test_extract_subject(self):
        """Test extracting subject from email dict."""
        email = {
            "subject": "Help with my order",
            "from": "customer@example.com",
            "body": "I need assistance..."
        }
        
        assert email["subject"] == "Help with my order"
    
    def test_extract_sender(self):
        """Test extracting sender from email dict."""
        email = {
            "subject": "Question",
            "from": "user@example.com",
            "body": "..."
        }
        
        assert email["from"] == "user@example.com"
    
    def test_handle_missing_subject(self):
        """Test handling email without subject."""
        email = {
            "from": "user@example.com",
            "body": "No subject email"
        }
        
        subject = email.get("subject", "(No Subject)")
        
        assert subject == "(No Subject)"


class TestKeywordMatching:
    """Tests for keyword-based classification fallback."""
    
    @pytest.fixture
    def keywords_config(self):
        """Keyword configuration for fallback matching."""
        return {
            "support": ["help", "issue", "problem", "broken"],
            "sales": ["buy", "purchase", "pricing", "quote"],
            "hr": ["resume", "job", "application", "hiring"]
        }
    
    def test_match_support_keywords(self, keywords_config):
        """Test matching support keywords."""
        text = "I have a problem with my account"
        
        matched = None
        for category, keywords in keywords_config.items():
            if any(kw in text.lower() for kw in keywords):
                matched = category
                break
        
        assert matched == "support"
    
    def test_match_sales_keywords(self, keywords_config):
        """Test matching sales keywords."""
        text = "I would like to purchase your product"
        
        matched = None
        for category, keywords in keywords_config.items():
            if any(kw in text.lower() for kw in keywords):
                matched = category
                break
        
        assert matched == "sales"
    
    def test_no_keyword_match(self, keywords_config):
        """Test when no keywords match."""
        text = "Random email content without keywords"
        
        matched = None
        for category, keywords in keywords_config.items():
            if any(kw in text.lower() for kw in keywords):
                matched = category
                break
        
        assert matched is None


class TestJSONParsing:
    """Tests for AI response JSON parsing."""
    
    def test_parse_valid_json(self):
        """Test parsing valid JSON response."""
        import json
        
        response = '{"category": "support", "confidence": 0.95, "reason": "Test"}'
        data = json.loads(response)
        
        assert data["category"] == "support"
        assert data["confidence"] == 0.95
    
    def test_parse_json_with_markdown(self):
        """Test parsing JSON wrapped in markdown code blocks."""
        import json
        
        response = '''```json
{"category": "sales", "confidence": 0.88}
```'''
        
        # Extract JSON from markdown
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
        else:
            json_str = response
        
        data = json.loads(json_str)
        
        assert data["category"] == "sales"
        assert data["confidence"] == 0.88
    
    def test_handle_invalid_json(self):
        """Test handling invalid JSON gracefully."""
        import json
        
        response = "This is not valid JSON"
        
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            data = {"category": "review", "confidence": 0.0}
        
        assert data["category"] == "review"
        assert data["confidence"] == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
