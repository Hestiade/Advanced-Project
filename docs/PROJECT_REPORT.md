# SEN0414 Advanced Programming - Project Report

## AI Mail Redirection Agent

**Student:** [Your Name]  
**Course:** SEN0414 Advanced Programming  
**Instructor:** Yusuf Altunel, PhD  
**Date:** January 2026  
**University:** Istanbul Kültür University

---

## 1. Introduction

### 1.1 Problem Statement

Organizations receive hundreds of emails daily that need to be routed to appropriate departments. Manual email sorting is:
- Time-consuming
- Error-prone
- Inconsistent
- Not scalable

### 1.2 Proposed Solution

An AI-powered email classification and routing system that:
- Automatically analyzes incoming emails using LLMs
- Classifies emails into predefined categories
- Routes emails to appropriate department mailboxes
- Provides a real-time monitoring dashboard

### 1.3 Target Audience

- Small to medium businesses
- IT administrators
- Customer service departments
- Any organization with multi-department email handling

---

## 2. Technical Implementation

### 2.1 System Architecture

The system follows a modular architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│                    Web Dashboard                         │
│                  (Flask + SocketIO)                      │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                   Core Application                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │  IMAP    │→ │   AI     │→ │  Router  │→ │  SMTP   │ │
│  │  Client  │  │ Analyzer │  │  Engine  │  │  Client │ │
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘ │
└─────────────────────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                   AI Providers                           │
│            Ollama (Local) │ Gemini (Cloud)              │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Core Components

| Component | Purpose | Key Classes |
|-----------|---------|-------------|
| Client | Email protocol handling | `IMAPClient`, `SMTPClient` |
| Analyzer | AI classification | `OllamaAnalyzer`, `GeminiAnalyzer` |
| Router | Routing logic | `EmailRouter`, `RoutingEngine` |
| Config | Configuration management | `AppConfig`, `load_config()` |

### 2.3 Technology Stack

- **Language:** Python 3.10+
- **Web Framework:** Flask with Flask-SocketIO
- **Email Protocols:** IMAP, SMTP
- **AI Providers:** Ollama, Google Gemini
- **Mail Server:** Maddy
- **Configuration:** YAML, python-dotenv

---

## 3. Python Features Demonstrated

### 3.1 Object-Oriented Programming

```python
class IMAPClient:
    """IMAP client with context manager support."""
    
    def __init__(self, host: str, port: int, ...):
        self.host = host
        self.port = port
        
    def __enter__(self):
        self.connect()
        return self
        
    def __exit__(self, *args):
        self.disconnect()
        
    def fetch_unread(self) -> Iterator[EmailMessage]:
        """Generator yielding unread emails."""
        for uid in self._get_unread_uids():
            yield self._fetch_email(uid)
```

### 3.2 Type Hints

```python
from typing import Optional, Iterator
from dataclasses import dataclass

@dataclass
class AnalysisResult:
    category: str
    confidence: float
    reason: Optional[str] = None
    
def analyze_email(email: EmailMessage) -> AnalysisResult:
    ...
```

### 3.3 Context Managers

```python
# Using IMAP client as context manager
with IMAPClient(host, port, user, password) as client:
    for email in client.fetch_unread():
        process(email)
# Connection automatically closed
```

### 3.4 Decorators

```python
from functools import wraps

def log_processing(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"Processing started")
        result = func(*args, **kwargs)
        logger.info(f"Processing completed")
        return result
    return wrapper
```

### 3.5 Generators

```python
def fetch_unread(self) -> Iterator[EmailMessage]:
    """Memory-efficient email iteration."""
    uids = self._search_unread()
    for uid in uids:
        yield self._fetch_single(uid)  # One at a time
```

### 3.6 Exception Handling

```python
try:
    result = self.analyzer.analyze(email)
except ConnectionError as e:
    logger.error(f"AI provider unavailable: {e}")
    result = self._fallback_classification(email)
except JSONDecodeError:
    logger.warning("Invalid AI response, using default")
    result = AnalysisResult(category="review", confidence=0.0)
```

### 3.7 Module Organization

```
mail_agent/
├── __init__.py          # Package exports
├── analyzer/
│   ├── __init__.py      # Analyzer factory
│   ├── base.py          # Abstract base class
│   ├── ollama.py        # Ollama implementation
│   └── gemini.py        # Gemini implementation
├── client/
│   ├── __init__.py
│   ├── imap_client.py
│   └── smtp_client.py
└── config/
    ├── __init__.py
    ├── loader.py
    └── models.py
```

---

## 4. AI Integration (AI4SE)

### 4.1 LLM Integration

The system integrates with two AI providers:

1. **Ollama** - Local LLM server
   - Models: qwen3:14b, llama3, etc.
   - Advantage: No API costs, data privacy

2. **Google Gemini** - Cloud AI
   - Models: gemini-pro
   - Advantage: High accuracy, no local GPU needed

### 4.2 Prompt Engineering

```python
CLASSIFICATION_PROMPT = """
You are an email classifier for a company. Analyze the email below 
and classify it into one of these categories:
- support: Customer issues, help requests
- sales: Purchase inquiries, quotes
- hr: Job applications, HR matters
- legal: Legal documents, contracts
- it: Technical requests, system access
- promotions: Marketing, newsletters
- vendors: Supplier communications

Email:
Subject: {subject}
From: {sender}
Body: {body}

Respond with JSON only:
{{"category": "...", "confidence": 0.0-1.0, "reason": "..."}}
"""
```

### 4.3 Response Handling

```python
def parse_ai_response(response: str) -> AnalysisResult:
    """Extract structured data from AI response."""
    # Handle markdown code blocks
    if "```json" in response:
        response = response.split("```json")[1].split("```")[0]
    
    data = json.loads(response)
    return AnalysisResult(
        category=data["category"],
        confidence=float(data["confidence"]),
        reason=data.get("reason")
    )
```

---

## 5. Testing

### 5.1 Test Coverage

| Module | Coverage |
|--------|----------|
| mail_agent.router | 85% |
| mail_agent.analyzer | 78% |
| mail_agent.client | 72% |
| **Overall** | **80%** |

### 5.2 Test Types

- **Unit Tests:** Individual function testing
- **Integration Tests:** Component interaction
- **Mock Tests:** AI provider simulation

### 5.3 Sample Test

```python
def test_email_classification():
    analyzer = MockAnalyzer()
    email = create_test_email(
        subject="Help with my order",
        body="I need assistance with order #123"
    )
    
    result = analyzer.analyze(email)
    
    assert result.category == "support"
    assert result.confidence > 0.8
```

---

## 6. User Interface

### 6.1 Web Dashboard

The Flask-based dashboard provides:
- Real-time email processing status
- Statistics and metrics
- Log viewer
- Manual controls

### 6.2 Control Panel

Interactive CLI for system management:
- Start/stop services
- View logs
- Manage mail accounts

---

## 7. Conclusion

### 7.1 Achievements

- ✅ Fully functional email routing system
- ✅ AI-powered classification with two provider options
- ✅ Real-time web dashboard
- ✅ Modular, maintainable code structure
- ✅ Comprehensive documentation

### 7.2 Lessons Learned

- LLM prompt engineering requires iteration
- Error handling is critical for AI integration
- Real-time updates enhance user experience
- Modular design simplifies testing

### 7.3 Future Improvements

- Multi-mailbox monitoring
- Custom category training
- AI provider fallback chain
- Mobile-responsive dashboard

---

## Appendix A: Installation

See [SETUP.md](../SETUP.md) for detailed installation instructions.

## Appendix B: API Reference

See [docs/ARCHITECTURE.md](ARCHITECTURE.md) for technical details.

## Appendix C: Configuration

See [config.example.yaml](../config.example.yaml) for configuration options.
