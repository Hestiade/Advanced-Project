"""
Ollama-powered email analyzer (Qwen3-friendly)
- LLM-first classification
- STRICT JSON output (single JSON object only)
- Robust parsing (extracts JSON even if model adds stray text)
- Retries on invalid / empty output
- Handles Ollama cases where "response" is empty (optionally falls back to "thinking" for debugging)
"""

import os
import json
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests


# ----------------------------
# If your project already has this model, delete the fallback dataclass below
# and import from your existing .models instead.
# from .models import AnalysisResult
# ----------------------------
@dataclass
class AnalysisResult:
    forward_to: str
    category: str
    confidence: float
    reasoning: str
    additional_destinations: List[str] = None
    raw_response: str = ""  # For debugging LLM output


# ----------------------------
# Production-grade STRICT JSON system prompt for Qwen3
# (shorter than your original; avoids token burn)
# ----------------------------
QWEN_SYSTEM_PROMPT_TEMPLATE = """You are an automated email classification engine for {company_name} ({company_mailbox}).

CRITICAL OUTPUT RULES (NON-NEGOTIABLE):
- Output ONLY a single valid JSON object.
- NO explanations. NO thinking. NO markdown. NO code blocks.
- First character MUST be "{{" and last character MUST be "}}".
- All fields are REQUIRED.
- risk_flags MUST always be an array (can be empty).
- reason MUST be max 20 words.
- If unsure, still output JSON.

REQUIRED JSON SCHEMA:
{{
  "category": "promotions|sales|vendors|hr|it|legal|support|spam|unknown",
  "action": "forward|needs_review|no_forward|spam",
  "forward_to": "company@mail.local|hr@mail.local|it@mail.local|legal@mail.local|sales@mail.local|support@mail.local|vendors@mail.local|promotions@mail.local|spam@mail.local|null",
  "confidence": 0.0,
  "risk_flags": [],
  "reason": ""
}}

CONFIDENCE CALIBRATION (CRITICAL - vary your scores):
- 0.90-1.00: Unmistakably clear (e.g., invoice with amount, obvious phishing link)
- 0.75-0.89: Strong signals but minor ambiguity (e.g., vendor email without invoice number)
- 0.60-0.74: Multiple categories possible, best guess (e.g., could be sales or support)
- 0.40-0.59: Genuinely uncertain, weak signals
- Below 0.40: Near-random guess, needs human review
DO NOT default to 0.95. Calibrate honestly based on actual clarity.

CLASSIFICATION RULES (priority order):
1) SPAM (highest priority)
   - credential phishing, verification links, password reset/expiry requests
   - dating/romance offers
   - lottery/crypto/inheritance/scams
   => category=spam, action=spam, forward_to=spam@mail.local

2) HIGH-RISK FINANCE (never auto-forward)
   - wire transfer, bank/IBAN change, payment instruction change, gift card requests
   => category=vendors, action=needs_review, forward_to=vendors@mail.local
   => risk_flags MUST include at least one of: "wire_transfer","bank_change","payment_instruction","gift_card"

3) VENDORS
   - invoices, payment reminders, purchase orders, supplier onboarding
   => category=vendors, action=forward, forward_to=vendors@mail.local

4) SALES (only if they want to BUY from us)
   => category=sales, action=forward, forward_to=sales@mail.local

5) HR
   => category=hr, action=forward, forward_to=hr@mail.local

6) IT
   - security questionnaires, system alerts, vulnerabilities, SSL expiry
   => category=it, action=forward, forward_to=it@mail.local

7) LEGAL
   - NDA/MSA/contracts, disputes, cease & desist, subpoenas
   => category=legal, action=forward, forward_to=legal@mail.local

8) SUPPORT
   - customer complaints, refunds, bug reports, service issues
   => category=support, action=forward, forward_to=support@mail.local

9) PROMOTIONS
   - newsletters, cold outreach selling to us, marketing offers
   => category=promotions, action=forward, forward_to=promotions@mail.local

10) UNKNOWN
   => category=unknown, action=needs_review, forward_to=company@mail.local

FINAL RULE: Output ONLY the JSON object. No other text.
"""


class OllamaAnalyzer:
    """
    LLM-first email analyzer with strict JSON output.

    Key improvements vs typical implementations:
    - Bigger num_predict default so JSON isn't cut off
    - Retries if model returns empty/invalid JSON
    - Strong JSON extractor and sanitizer
    - Optional fallback to 'thinking' if Ollama returns response="" (useful for debugging)
    """

    def __init__(
        self,
        model: str,
        destinations: List[Dict[str, Any]],
        base_url: Optional[str] = None,
        company_name: str = "TechCorp Industries",
        company_mailbox: str = "company@mail.local",
        request_timeout: int = 120,
        max_retries: int = 2,
        retry_backoff_sec: float = 0.4,
        debug_accept_thinking_field: bool = False,  # set True ONLY for debugging
    ):
        self.model = model
        self.destinations = destinations
        self.base_url = base_url or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.company_name = company_name
        self.company_mailbox = company_mailbox
        self.request_timeout = request_timeout
        self.max_retries = max_retries
        self.retry_backoff_sec = retry_backoff_sec
        self.debug_accept_thinking_field = debug_accept_thinking_field

        self.system_prompt = QWEN_SYSTEM_PROMPT_TEMPLATE.format(
            company_name=company_name,
            company_mailbox=company_mailbox,
        )

        # Optional mapping if you want quick routing lookup elsewhere
        self.category_to_email = {
            "support": "support@mail.local",
            "sales": "sales@mail.local",
            "vendors": "vendors@mail.local",
            "hr": "hr@mail.local",
            "it": "it@mail.local",
            "legal": "legal@mail.local",
            "promotions": "promotions@mail.local",
            "spam": "spam@mail.local",
            "unknown": company_mailbox,
        }

    def analyze(self, email_data: Dict[str, Any]) -> AnalysisResult:
        """Analyze email using Ollama/Qwen and return a parsed AnalysisResult."""
        subject = (email_data.get("subject") or "").strip()
        body = (email_data.get("body") or "").strip()
        from_addr = (email_data.get("from") or email_data.get("from_addr") or "Unknown").strip()

        # Keep prompt small to reduce truncation / improve determinism
        # (Model already has rules in system prompt)
        user_prompt = (
            "Classify this email. Output ONLY the JSON object.\n\n"
            f"From: {from_addr}\n"
            f"Subject: {subject}\n"
            "Body:\n"
            f"{body[:1200]}"
        )

        last_err: Optional[str] = None
        last_raw: str = ""

        for attempt in range(self.max_retries + 1):
            try:
                result = self._call_ollama(user_prompt=user_prompt)
                raw = (result.get("response") or "").strip()
                last_raw = raw

                # Some setups/models may place content in "thinking".
                # This is NOT ideal for production; keep off unless debugging.
                if not raw and self.debug_accept_thinking_field:
                    raw = (result.get("thinking") or "").strip()
                    last_raw = raw

                if not raw:
                    raise ValueError("Empty LLM output (response was blank)")

                parsed = self._parse_response(raw)
                parsed.raw_response = raw
                return parsed

            except Exception as e:
                last_err = str(e)
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff_sec * (attempt + 1))
                    continue

        return AnalysisResult(
            forward_to="",
            category="review",
            confidence=0.0,
            reasoning=f"LLM/parse error after retries: {last_err}",
            additional_destinations=[],
            raw_response=last_raw,
        )

    def _call_ollama(self, user_prompt: str) -> Dict[str, Any]:
        """Low-level call to Ollama /api/generate"""
        payload = {
            "model": self.model,
            "system": self.system_prompt,
            "prompt": user_prompt,
            "stream": False,
            # Disable thinking mode for extra thinking models (e.g., Qwen3)
            "think": False,
            "options": {
                # Deterministic formatting
                "temperature": 0,
                # Enough tokens to actually output JSON (your previous 120 was too small)
                "num_predict": 512,
            },
        }

        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.request_timeout,
        )
        response.raise_for_status()
        return response.json()

    # ----------------------------
    # Parsing / Sanitizing
    # ----------------------------

    def _parse_response(self, response_text: str) -> AnalysisResult:
        """
        Parse STRICT JSON response.
        Extract JSON object from any surrounding text (defensive),
        then normalize fields into AnalysisResult.
        """
        data = self._extract_json_object(response_text)

        # Normalize fields
        category = str(data.get("category", "unknown")).strip().lower()
        action = str(data.get("action", "needs_review")).strip().lower()
        forward_to = data.get("forward_to", None)
        reason = str(data.get("reason", "")).strip()
        risk_flags = data.get("risk_flags", [])
        confidence = self._normalize_confidence(data.get("confidence", 0.0))

        # Ensure list
        if not isinstance(risk_flags, list):
            risk_flags = [str(risk_flags)]

        # Add risk flags into reasoning string (optional)
        if risk_flags:
            flags_str = ", ".join(str(f) for f in risk_flags)
            reason = f"⚠️ [{flags_str}] {reason}".strip()

        # Normalize forward_to
        if forward_to is None:
            forward_to_str = ""
        else:
            forward_to_str = str(forward_to).strip()
            if forward_to_str.lower() == "null":
                forward_to_str = ""

        # Map actions to result behavior
        if action == "spam":
            # always to spam mailbox
            fwd = forward_to_str or "spam@mail.local"
            return AnalysisResult(
                forward_to=fwd,
                category="spam",
                confidence=confidence,
                reasoning=f"🚨 {reason}".strip() if reason else "🚨 Phishing/scam detected",
                additional_destinations=[],
            )

        if action == "forward" and forward_to_str:
            return AnalysisResult(
                forward_to=forward_to_str,
                category=category,
                confidence=confidence,
                reasoning=reason or "Forwarded by policy",
                additional_destinations=[],
            )

        if action == "no_forward":
            return AnalysisResult(
                forward_to="",
                category=category,
                confidence=confidence,
                reasoning=reason or "No forwarding required",
                additional_destinations=[],
            )

        # needs_review or unknown -> review
        if action in ("needs_review", "needs-review"):
            return AnalysisResult(
                forward_to=forward_to_str,  # may still carry suggested mailbox
                category=category,
                confidence=confidence,
                reasoning=reason or "Needs manual review",
                additional_destinations=[],
            )

        # Any unknown action -> review
        return AnalysisResult(
            forward_to="",
            category="review",
            confidence=0.0,
            reasoning=f"Unrecognized action '{action}'. Needs manual review.",
            additional_destinations=[],
        )

    def _extract_json_object(self, text: str) -> Dict[str, Any]:
        """
        Extract the first valid JSON object from text.
        This is defensive: ideally the model returns ONLY JSON.
        """
        s = (text or "").strip()

        # Fast path: already valid JSON
        if s.startswith("{") and s.endswith("}"):
            try:
                return json.loads(s)
            except json.JSONDecodeError:
                pass

        # Try to find a JSON object region
        # This matches the largest {...} block; good enough for single-object outputs
        m = re.search(r"\{[\s\S]*\}", s)
        if not m:
            raise ValueError("No JSON found in response")

        candidate = m.group(0).strip()

        # If model used smart quotes or weird whitespace, fix common issues carefully
        candidate = self._sanitize_common_json_issues(candidate)

        try:
            return json.loads(candidate)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e

    @staticmethod
    def _sanitize_common_json_issues(s: str) -> str:
        """
        Minimal, safe sanitization.
        Avoid dangerous transforms like replacing all apostrophes globally.
        """
        # Remove UTF-8 BOM if present
        s = s.lstrip("\ufeff")

        # Replace smart quotes with normal quotes
        s = s.replace("“", '"').replace("”", '"').replace("’", "'")

        # Remove trailing commas before } or ]
        s = re.sub(r",\s*([}\]])", r"\1", s)

        return s

    @staticmethod
    def _normalize_confidence(val: Any) -> float:
        try:
            if isinstance(val, (int, float)):
                x = float(val)
                if x > 1.0:
                    x = x / 100.0
                if x < 0.0:
                    return 0.0
                if x > 1.0:
                    return 1.0
                return x
            # string numbers
            if isinstance(val, str):
                x = float(val.strip())
                if x > 1.0:
                    x = x / 100.0
                return max(0.0, min(1.0, x))
        except Exception:
            pass
        return 0.0


# ----------------------------
# Optional: quick local test runner
# ----------------------------
if __name__ == "__main__":
    analyzer = OllamaAnalyzer(
        model=os.getenv("OLLAMA_MODEL", "qwen3:14b"),
        destinations=[],
        base_url=os.getenv("OLLAMA_HOST", "http://192.168.1.102:11434"),
        debug_accept_thinking_field=False,  # set True only if response is blank and you need diagnosis
    )

    sample_email = {
        "from": "deniz@mail.local",
        "subject": "Invoice INV-2025-0042 - Payment Due",
        "body": "Please find attached Invoice #INV-2025-0042 for cloud hosting services rendered in January 2025.\n"
                "Amount Due: $4,850.00\nDue Date: February 15, 2025\n"
                "Payment can be made via wire transfer to the account details on the invoice.",
    }

    res = analyzer.analyze(sample_email)
    print(res)
