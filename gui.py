#!/usr/bin/env python3
"""GUI Dashboard for the AI Mail Redirection Agent."""

import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from mail_agent import load_config, Router, IMAPClient, SMTPClient


@dataclass
class EmailStatus:
    """Track processing status for an email."""
    uid: str
    from_addr: str
    subject: str
    status: str = "Pending"
    forward_to: list[str] = field(default_factory=list)
    category: str = ""
    confidence: float = 0.0


class MailAgentGUI:
    """GUI Dashboard for the Mail Redirection Agent."""
    
    def __init__(self):
        self.config = load_config()
        self.running = False
        self.emails: list[EmailStatus] = []
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("AI Mail Redirection Agent")
        self.root.geometry("1100x750")
        self.root.configure(bg="#1e1e2e")
        
        self._setup_styles()
        self._create_widgets()
        
    def _setup_styles(self):
        """Setup ttk styles for dark theme."""
        style = ttk.Style()
        style.theme_use("clam")
        
        # Dark theme colors
        bg_color = "#1e1e2e"
        fg_color = "#cdd6f4"
        accent = "#89b4fa"
        
        style.configure(".", background=bg_color, foreground=fg_color)
        style.configure("TFrame", background=bg_color)
        style.configure("TLabel", background=bg_color, foreground=fg_color, font=("Consolas", 10))
        style.configure("Title.TLabel", font=("Consolas", 16, "bold"), foreground=accent)
        style.configure("Status.TLabel", font=("Consolas", 11))
        style.configure("TButton", font=("Consolas", 10))
        style.configure("Treeview", 
                       background="#313244", 
                       foreground=fg_color, 
                       fieldbackground="#313244",
                       font=("Consolas", 9))
        style.configure("Treeview.Heading", 
                       background="#45475a", 
                       foreground=fg_color,
                       font=("Consolas", 10, "bold"))
        
    def _create_widgets(self):
        """Create the GUI widgets."""
        # Header
        header = ttk.Frame(self.root)
        header.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(header, text="📬 AI Mail Redirection Agent", style="Title.TLabel").pack(side=tk.LEFT)
        
        # Status indicator
        self.status_var = tk.StringVar(value="● Stopped")
        self.status_label = ttk.Label(header, textvariable=self.status_var, style="Status.TLabel")
        self.status_label.pack(side=tk.RIGHT, padx=10)
        
        # Account info
        info_frame = ttk.Frame(self.root)
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(info_frame, text=f"Account: {self.config.email.address}").pack(side=tk.LEFT)
        ai_name = self.config.ollama_model if self.config.ollama_model else "Gemini"
        ttk.Label(info_frame, text=f"AI: {ai_name}").pack(side=tk.LEFT, padx=20)
        ttk.Label(info_frame, text=f"Categories: {len(self.config.ai_routing.destinations)}").pack(side=tk.LEFT, padx=20)
        
        # Control buttons
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.start_btn = ttk.Button(btn_frame, text="▶ Start Watching", command=self._start_watching)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="⏹ Stop", command=self._stop_watching, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.refresh_btn = ttk.Button(btn_frame, text="🔄 Refresh Now", command=self._refresh_once)
        self.refresh_btn.pack(side=tk.LEFT, padx=5)
        
        # Interval selector
        ttk.Label(btn_frame, text="Check every:").pack(side=tk.LEFT, padx=(20, 5))
        self.interval_var = tk.StringVar(value="30")
        interval_combo = ttk.Combobox(btn_frame, textvariable=self.interval_var, width=5, 
                                      values=["10", "30", "60", "120"])
        interval_combo.pack(side=tk.LEFT)
        ttk.Label(btn_frame, text="seconds").pack(side=tk.LEFT, padx=5)
        
        # Email table
        table_frame = ttk.Frame(self.root)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ("from", "subject", "status", "category", "confidence", "forward_to")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
        
        self.tree.heading("from", text="From")
        self.tree.heading("subject", text="Subject")
        self.tree.heading("status", text="Status")
        self.tree.heading("category", text="Category")
        self.tree.heading("confidence", text="Confidence")
        self.tree.heading("forward_to", text="Forward To")
        
        self.tree.column("from", width=150)
        self.tree.column("subject", width=280)
        self.tree.column("status", width=100)
        self.tree.column("category", width=80)
        self.tree.column("confidence", width=80)
        self.tree.column("forward_to", width=200)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Stats bar
        stats_frame = ttk.Frame(self.root)
        stats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.stats_var = tk.StringVar(value="Processed: 0 | Forwarded: 0 | Skipped: 0")
        ttk.Label(stats_frame, textvariable=self.stats_var).pack(side=tk.LEFT)
        
        # Log area
        log_label = ttk.Label(self.root, text="Activity Log:")
        log_label.pack(anchor=tk.W, padx=10, pady=(10, 0))
        
        self.log_text = scrolledtext.ScrolledText(
            self.root, height=8, bg="#313244", fg="#cdd6f4", 
            font=("Consolas", 9), insertbackground="#cdd6f4"
        )
        self.log_text.pack(fill=tk.X, padx=10, pady=5)
        
        self._log("Ready. Click 'Start Watching' to begin monitoring inbox.")
        
    def _log(self, message: str):
        """Add message to log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        
    def _update_table(self):
        """Update the email table."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Counters
        forwarded = 0
        skipped = 0
        
        # Add emails
        for email in self.emails:
            status_icon = {
                "Pending": "⏳",
                "Processing": "⚙️",
                "Forwarded": "✅",
                "Skipped": "⏭️",
                "Error": "❌",
            }.get(email.status, "")
            
            if email.status == "Forwarded":
                forwarded += 1
            elif email.status == "Skipped":
                skipped += 1
            
            confidence_str = f"{email.confidence:.0%}" if email.confidence else ""
            forward_str = ", ".join(email.forward_to) if email.forward_to else "-"
            
            self.tree.insert("", tk.END, values=(
                email.from_addr[:25],
                email.subject[:45],
                f"{status_icon} {email.status}",
                email.category,
                confidence_str,
                forward_str,
            ))
        
        # Update stats
        self.stats_var.set(f"Processed: {len(self.emails)} | Forwarded: {forwarded} | Skipped: {skipped}")
        self.root.update_idletasks()
        
    def _start_watching(self):
        """Start the watching loop."""
        self.running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_var.set("● Running")
        self._log("Started watching inbox...")
        
        # Start background thread
        thread = threading.Thread(target=self._watch_loop, daemon=True)
        thread.start()
        
    def _stop_watching(self):
        """Stop the watching loop."""
        self.running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_var.set("● Stopped")
        self._log("Stopped watching.")
        
    def _refresh_once(self):
        """Refresh emails once."""
        thread = threading.Thread(target=self._process_emails, daemon=True)
        thread.start()
        
    def _watch_loop(self):
        """Background loop to watch emails."""
        while self.running:
            self._process_emails()
            try:
                interval = int(self.interval_var.get())
            except ValueError:
                interval = 30
            time.sleep(interval)
            
    def _process_emails(self):
        """Fetch and process unread emails."""
        self._log("Checking for new emails...")
        
        try:
            router = Router(
                rules=self.config.rules,
                ai_enabled=self.config.ai_routing.enabled,
                gemini_api_key=self.config.gemini_api_key,
                ollama_model=self.config.ollama_model,
                ai_destinations=self.config.ai_routing.destinations,
                default_action=self.config.default_action,
            )
            
            smtp = SMTPClient(
                host=self.config.email.smtp_host,
                port=self.config.email.smtp_port,
                address=self.config.email.address,
                password=self.config.email.password,
                use_tls=self.config.email.use_tls,
            )
            
            imap = IMAPClient(
                host=self.config.email.imap_host,
                port=self.config.email.imap_port,
                address=self.config.email.address,
                password=self.config.email.password,
                use_ssl=self.config.email.use_ssl,
            )
            
            with imap:
                emails = list(imap.fetch_unread())
                
                if not emails:
                    self._log("No unread emails found.")
                    return
                
                self._log(f"Found {len(emails)} unread email(s)")
                
                # Add emails to list with Pending status
                self.emails = []
                for email in emails:
                    self.emails.append(EmailStatus(
                        uid=email.uid,
                        from_addr=email.from_addr,
                        subject=email.subject,
                        status="Pending"
                    ))
                self.root.after(0, self._update_table)
                
                # Process each email
                for i, email in enumerate(emails):
                    self.emails[i].status = "Processing"
                    self.root.after(0, self._update_table)
                    
                    decision = router.decide(email)
                    
                    if decision.should_forward:
                        try:
                            # Forward to ALL destinations (primary + additional)
                            all_destinations = decision.all_destinations
                            
                            for dest in all_destinations:
                                smtp.forward_email(email, dest)
                                self._log(f"  → Forwarded to: {dest}")
                            
                            imap.mark_as_read(email.uid)
                            
                            self.emails[i].status = "Forwarded"
                            self.emails[i].forward_to = all_destinations
                            self._log(f"✓ {email.subject[:30]} → {len(all_destinations)} destination(s)")
                        except Exception as e:
                            self.emails[i].status = "Error"
                            self._log(f"✗ Error forwarding: {e}")
                    else:
                        self.emails[i].status = "Skipped"
                        self._log(f"⏭ Skipped: {email.subject[:30]}")
                    
                    if decision.ai_result:
                        self.emails[i].category = decision.ai_result.category
                        self.emails[i].confidence = decision.ai_result.confidence
                    
                    self.root.after(0, self._update_table)
                    
        except Exception as e:
            self._log(f"Error: {e}")
            
    def run(self):
        """Start the GUI."""
        self.root.mainloop()


def main():
    """Entry point."""
    app = MailAgentGUI()
    app.run()


if __name__ == "__main__":
    main()
