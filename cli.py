#!/usr/bin/env python3
"""CLI interface for the AI Mail Redirection Agent."""

import time
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from mail_agent import load_config, Router, IMAPClient, SMTPClient

console = Console()


@click.group()
@click.option("--config", "-c", default="config.yaml", help="Path to config file")
@click.pass_context
def cli(ctx, config):
    """AI Mail Redirection Agent - Intelligent email routing."""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config


@cli.command()
@click.option("--dry-run", is_flag=True, help="Don't actually forward emails")
@click.pass_context
def run(ctx, dry_run):
    """Process unread emails once."""
    config = load_config(ctx.obj["config_path"])
    
    if not config.email.address or not config.email.password:
        console.print("[red]Error:[/] Email credentials not configured. Set EMAIL_ADDRESS and EMAIL_PASSWORD in .env")
        return
    
    router = Router(
        rules=config.rules,
        ai_enabled=config.ai_routing.enabled,
        gemini_api_key=config.gemini_api_key,
        ollama_model=config.ollama_model,
        ai_destinations=config.ai_routing.destinations,
        default_action=config.default_action,
    )
    
    smtp = SMTPClient(
        host=config.email.smtp_host,
        port=config.email.smtp_port,
        address=config.email.address,
        password=config.email.password,
        use_tls=config.email.use_tls,
    )
    
    console.print(Panel.fit(
        f"[bold blue]AI Mail Redirector[/]\n"
        f"Account: {config.email.address}\n"
        f"Rules: {len(config.rules)} | AI: {'enabled' if config.ai_routing.enabled else 'disabled'}",
        title="Starting"
    ))
    
    try:
        imap = IMAPClient(
            host=config.email.imap_host,
            port=config.email.imap_port,
            address=config.email.address,
            password=config.email.password,
            use_ssl=config.email.use_ssl,
        )
        
        with imap:
            emails = list(imap.fetch_unread())
            
            if not emails:
                console.print("[dim]No unread emails found.[/]")
                return
            
            console.print(f"\nFound [bold]{len(emails)}[/] unread email(s)\n")
            
            table = Table(title="Email Processing Results")
            table.add_column("From", style="cyan", max_width=30)
            table.add_column("Subject", style="white", max_width=40)
            table.add_column("Decision", style="green")
            table.add_column("Forward To", style="yellow")
            
            for email in emails:
                decision = router.decide(email)
                
                if decision.should_forward and not dry_run:
                    try:
                        smtp.forward_email(email, decision.forward_to)
                        imap.mark_as_read(email.uid)
                        status = "✓ Forwarded"
                    except Exception as e:
                        status = f"✗ Error: {e}"
                elif decision.should_forward:
                    status = "(dry-run)"
                else:
                    status = "Skipped"
                
                table.add_row(
                    email.from_addr[:30],
                    email.subject[:40],
                    decision.source,
                    decision.forward_to or "-"
                )
            
            console.print(table)
            
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")


@cli.command()
@click.option("--interval", "-i", default=60, help="Check interval in seconds")
@click.option("--dry-run", is_flag=True, help="Don't actually forward emails")
@click.pass_context
def watch(ctx, interval, dry_run):
    """Continuously monitor inbox and process emails."""
    config = load_config(ctx.obj["config_path"])
    
    if not config.email.address or not config.email.password:
        console.print("[red]Error:[/] Email credentials not configured")
        return
    
    console.print(Panel.fit(
        f"[bold blue]Watching Inbox[/]\n"
        f"Account: {config.email.address}\n"
        f"Interval: {interval}s | Dry-run: {dry_run}",
        title="Daemon Mode"
    ))
    
    router = Router(
        rules=config.rules,
        ai_enabled=config.ai_routing.enabled,
        gemini_api_key=config.gemini_api_key,
        ollama_model=config.ollama_model,
        ai_destinations=config.ai_routing.destinations,
        default_action=config.default_action,
    )
    
    smtp = SMTPClient(
        host=config.email.smtp_host,
        port=config.email.smtp_port,
        address=config.email.address,
        password=config.email.password,
        use_tls=config.email.use_tls,
    )
    
    try:
        while True:
            try:
                imap = IMAPClient(
                    host=config.email.imap_host,
                    port=config.email.imap_port,
                    address=config.email.address,
                    password=config.email.password,
                    use_ssl=config.email.use_ssl,
                )
                
                with imap:
                    for email in imap.fetch_unread():
                        decision = router.decide(email)
                        
                        if decision.should_forward and not dry_run:
                            smtp.forward_email(email, decision.forward_to)
                            imap.mark_as_read(email.uid)
                            console.print(
                                f"[green]→[/] {email.subject[:40]} → {decision.forward_to}"
                            )
                        elif decision.should_forward:
                            console.print(
                                f"[dim](dry-run)[/] {email.subject[:40]} → {decision.forward_to}"
                            )
            except Exception as e:
                console.print(f"[yellow]Warning:[/] {e}")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        console.print("\n[dim]Stopped watching.[/]")


@cli.command()
@click.pass_context
def test(ctx):
    """Test configuration without processing emails."""
    config = load_config(ctx.obj["config_path"])
    
    console.print(Panel.fit("[bold]Configuration Test[/]", title="Test Mode"))
    
    # Test email config
    console.print("\n[bold]Email Configuration:[/]")
    console.print(f"  IMAP: {config.email.imap_host}:{config.email.imap_port} (SSL: {config.email.use_ssl})")
    console.print(f"  SMTP: {config.email.smtp_host}:{config.email.smtp_port} (TLS: {config.email.use_tls})")
    console.print(f"  Address: {config.email.address or '[red]NOT SET[/]'}")
    console.print(f"  Password: {'[green]SET[/]' if config.email.password else '[red]NOT SET[/]'}")
    
    # Test rules
    console.print(f"\n[bold]Rules ({len(config.rules)}):[/]")
    for rule in config.rules:
        console.print(f"  • {rule.name} → {rule.forward_to}")
    
    # Test AI config
    console.print(f"\n[bold]AI Routing:[/]")
    console.print(f"  Enabled: {config.ai_routing.enabled}")
    console.print(f"  API Key: {'[green]SET[/]' if config.gemini_api_key else '[red]NOT SET[/]'}")
    console.print(f"  Destinations: {len(config.ai_routing.destinations)}")
    
    # Try connection
    if config.email.address and config.email.password:
        console.print("\n[bold]Testing IMAP connection...[/]")
        try:
            imap = IMAPClient(
                host=config.email.imap_host,
                port=config.email.imap_port,
                address=config.email.address,
                password=config.email.password,
                use_ssl=config.email.use_ssl,
            )
            with imap:
                console.print("[green]✓ Successfully connected to IMAP server[/]")
        except Exception as e:
            console.print(f"[red]✗ Connection failed: {e}[/]")
    else:
        console.print("\n[yellow]⚠ Skipping connection test (credentials not set)[/]")


@cli.command("test-local")
@click.pass_context
def test_local(ctx):
    """Run a local test with mock mail server."""
    from mail_agent.testserver import TestMailServer
    from mail_agent.testserver.server import TestIMAPClient, TestSMTPClient
    from mail_agent import Router
    
    console.print(Panel.fit("[bold]Local Test Mode[/]", title="Testing with Mock Server"))
    
    # Create test server and add sample emails
    server = TestMailServer()
    
    server.add_test_email(
        from_addr="boss@company.com",
        to_addr="me@example.com",
        subject="Urgent: Q4 Report needed",
        body="Please send the Q4 report ASAP. This is urgent!"
    )
    
    server.add_test_email(
        from_addr="newsletter@news.com",
        to_addr="me@example.com",
        subject="Weekly Newsletter - December Edition",
        body="Here's your weekly digest of news and updates..."
    )
    
    server.add_test_email(
        from_addr="friend@gmail.com",
        to_addr="me@example.com",
        subject="Hey! Long time no see",
        body="How have you been? Let's catch up sometime!"
    )
    
    console.print(f"Added [bold]{len(server.emails)}[/] test emails\n")
    
    # Load config for rules
    config = load_config(ctx.obj["config_path"])
    
    router = Router(
        rules=config.rules,
        ai_enabled=False,  # Disable AI for local test
        default_action="skip",
    )
    
    # Process emails
    test_imap = TestIMAPClient(server)
    test_smtp = TestSMTPClient()
    
    table = Table(title="Local Test Results")
    table.add_column("From", style="cyan")
    table.add_column("Subject", style="white")
    table.add_column("Decision", style="green")
    table.add_column("Would Forward To", style="yellow")
    
    with test_imap:
        for email in test_imap.fetch_unread():
            decision = router.decide(email)
            
            if decision.should_forward:
                test_smtp.forward_email(email, decision.forward_to)
                test_imap.mark_as_read(email.uid)
            
            table.add_row(
                email.from_addr,
                email.subject[:40],
                decision.source,
                decision.forward_to or "-"
            )
    
    console.print(table)
    console.print(f"\n[dim]Emails that would be forwarded: {len(test_smtp.sent_emails)}[/]")


if __name__ == "__main__":
    cli()
