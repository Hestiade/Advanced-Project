#!/usr/bin/env python3
"""
Email Logger - Comprehensive logging for the AI Mail Redirection Agent.
Logs all email processing: incoming emails, AI responses, routing decisions, and actions.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

# Default log directory
LOG_DIR = Path(__file__).parent / "logs"


@dataclass
class EmailLogEntry:
    """A single email processing log entry."""
    timestamp: str
    uid: int
    from_addr: str
    to_addr: str
    subject: str
    body_preview: str  # First 500 chars
    
    # AI Analysis
    ai_action: str  # forward, spam, ignore, review
    ai_route_to: Optional[str]
    ai_category: str
    ai_confidence: float
    ai_reason: str
    ai_raw_response: str  # Full LLM response
    
    # Final decision
    final_action: str  # forwarded, skipped, quarantined, review, approved, rejected
    forward_destinations: list
    
    # Metadata
    processing_time_ms: int = 0
    error: Optional[str] = None


class EmailLogger:
    """Logger for email processing events."""
    
    def __init__(self, log_dir: str = None, session_id: str = None):
        self.log_dir = Path(log_dir) if log_dir else LOG_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Session-based log file (created once when logger starts)
        if session_id:
            self.session_id = session_id
        else:
            self.session_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        self.log_file = self.log_dir / f"email_log_{self.session_id}.jsonl"
        self.actions_file = self.log_dir / f"actions_{self.session_id}.jsonl"
    
    def log_email(
        self,
        uid: int,
        from_addr: str,
        to_addr: str,
        subject: str,
        body: str,
        ai_action: str = "",
        ai_route_to: str = None,
        ai_category: str = "",
        ai_confidence: float = 0.0,
        ai_reason: str = "",
        ai_raw_response: str = "",
        final_action: str = "",
        forward_destinations: list = None,
        processing_time_ms: int = 0,
        error: str = None
    ):
        """Log an email processing event."""
        entry = EmailLogEntry(
            timestamp=datetime.now().isoformat(),
            uid=uid,
            from_addr=from_addr,
            to_addr=to_addr,
            subject=subject,
            body_preview=body[:500] if body else "",
            ai_action=ai_action,
            ai_route_to=ai_route_to,
            ai_category=ai_category,
            ai_confidence=ai_confidence,
            ai_reason=ai_reason,
            ai_raw_response=ai_raw_response,
            final_action=final_action,
            forward_destinations=forward_destinations or [],
            processing_time_ms=processing_time_ms,
            error=error
        )
        
        # Append to JSONL file
        with open(self.log_file, "a") as f:
            f.write(json.dumps(asdict(entry)) + "\n")
        
        return entry
    
    def log_action(self, uid: int, action: str, destinations: list = None, error: str = None):
        """Log a follow-up action (approve/reject) for an existing email."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "uid": uid,
            "action": action,
            "destinations": destinations or [],
            "error": error
        }
        
        # Append to session-based actions log
        with open(self.actions_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def list_sessions(self) -> list:
        """List all available log sessions."""
        sessions = []
        for f in sorted(self.log_dir.glob("email_log_*.jsonl"), reverse=True):
            # Extract session_id from filename
            session_id = f.stem.replace("email_log_", "")
            sessions.append({
                "session_id": session_id,
                "file": str(f),
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            })
        return sessions
    
    def get_logs(self, session_id: str = None, limit: int = 100) -> list:
        """Get log entries for a specific session (or current session)."""
        if session_id is None:
            log_file = self.log_file
        else:
            log_file = self.log_dir / f"email_log_{session_id}.jsonl"
        
        if not log_file.exists():
            return []
        
        entries = []
        with open(log_file, "r") as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
        
        return entries[-limit:]
    
    def get_stats(self, date: str = None) -> dict:
        """Get processing statistics for a specific date."""
        logs = self.get_logs(date, limit=10000)
        
        stats = {
            "total": len(logs),
            "forwarded": 0,
            "spam": 0,
            "ignored": 0,
            "review": 0,
            "errors": 0,
            "by_route": {},
            "by_category": {},
            "avg_confidence": 0.0
        }
        
        confidence_sum = 0.0
        
        for log in logs:
            action = log.get("final_action", "")
            
            if action == "forwarded":
                stats["forwarded"] += 1
            elif action in ("spam", "quarantined"):
                stats["spam"] += 1
            elif action in ("ignored", "skipped"):
                stats["ignored"] += 1
            elif action == "review":
                stats["review"] += 1
            
            if log.get("error"):
                stats["errors"] += 1
            
            # Route stats
            route = log.get("ai_route_to")
            if route:
                stats["by_route"][route] = stats["by_route"].get(route, 0) + 1
            
            # Category stats
            cat = log.get("ai_category")
            if cat:
                stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1
            
            confidence_sum += log.get("ai_confidence", 0)
        
        if logs:
            stats["avg_confidence"] = round(confidence_sum / len(logs), 3)
        
        return stats


# Global logger instance
_logger = None


def get_logger() -> EmailLogger:
    """Get the global email logger instance."""
    global _logger
    if _logger is None:
        _logger = EmailLogger()
    return _logger


# Convenience functions
def log_email(**kwargs):
    """Log an email processing event."""
    return get_logger().log_email(**kwargs)


def log_action(uid: int, action: str, destinations: list = None, error: str = None):
    """Log a follow-up action."""
    return get_logger().log_action(uid, action, destinations, error)


def get_logs(date: str = None, limit: int = 100) -> list:
    """Get log entries."""
    return get_logger().get_logs(date, limit)


def get_stats(date: str = None) -> dict:
    """Get processing statistics."""
    return get_logger().get_stats(date)
