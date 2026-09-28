"""Command-line interface for the Autonomous AI Playwright Automation Framework."""

import argparse
import asyncio
import os
import shutil
import sys
from datetime import datetime

# Ensure UTF-8 output on Windows consoles to prevent cp1252 charmap encoding errors
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from core.orchestrator import AutomationOrchestrator
from config.settings import settings


console = Console(force_terminal=True, legacy_windows=False)




def render_banner(
    url: str,
    scenario: str,
    model: str,
    headed: bool = False,
    slowmo: int = 0,
) -> None:
    """Print an aesthetic Rich header panel."""
    banner_text = Text()
    banner_text.append("🤖 Autonomous Self-Healing E2E Test Automation\n", style="bold cyan")
    banner_text.append("Powered by Google Gemini & Playwright Python\n\n", style="italic white")
    banner_text.append(f"🌐 Target URL: {url}\n", style="bold yellow")
    banner_text.append(f"🎯 Scenario:   {scenario}\n", style="white")
    banner_text.append(f"🧠 Model:      {model}\n", style="dim green")
    mode_str = f"Headed (slowmo: {slowmo}ms)" if headed else "Headless"
    banner_text.append(f"🖥️ Mode:       {mode_str}\n", style="bold magenta" if headed else "dim cyan")
    banner_text.append(f"🕒 Timestamp:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="dim")

    console.print(Panel(banner_text, border_style="cyan", expand=False))


def status_style(status: str) -> str:
    """Map status codes to Rich color formatting."""
    s = status.upper()
    if s in ("PASSED", "SUCCESS", "COMPLETED"):
        return "[bold green]" + status + "[/bold green]"
    if s in ("RUNNING", "HEALING", "RE-TESTING"):
        return "[bold yellow]" + status + "[/bold yellow]"
    if s in ("FAILED", "RETRY_FAILED"):
        return "[bold red]" + status + "[/bold red]"
    if s in ("PATCHED",):
        return "[bold magenta]" + status + "[/bold magenta]"
    return "[white]" + status + "[/white]"


async def main_async() -> int:
    parser = argparse.ArgumentParser(
        description="Autonomous Self-Healing E2E Playwright Automation Framework"
    )
    parser.add_argument(
        "--url",
        type=str,
        required=True,
        help="Target web application URL (e.g., https://www.saucedemo.com)",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        required=True,
        help="Natural language test requirement/scenario",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Gemini model override (default from config/settings)",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        default=False,
        help="Launch the visible browser window (default: headless)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Explicitly run browser in headless mode (default behavior)",
    )
    parser.add_argument(
        "--slowmo",
        type=int,
        default=0,
        help="Delay between Playwright actions in milliseconds (e.g., 300 to 500 ms)",
    )
    parser.add_argument(
        "--max-healing",
        type=int,
        default=None,
        help="Maximum self-healing retry iterations (default: 3)",
    )

    parser.add_argument(
        "--serve-report",
        action="store_true",
        default=False,
        help="Automatically trigger 'allure serve' for generated results if Allure CLI is installed",
    )

    args = parser.parse_args()

    # Headless is default unless --headed is explicitly specified
    is_headed = args.headed and not args.headless

    active_model = args.model or settings.gemini_model or "gemini-3.7-flash"
    render_banner(args.url, args.scenario, active_model, headed=is_headed, slowmo=args.slowmo)

    events = []

    def handle_progress(step: str, status: str, details: str) -> None:
        events.append((step, status, details))
        console.print(
            f"  • [bold]{step:<24}[/bold] {status_style(status):<28} [dim]{details}[/dim]"
        )

    orchestrator = AutomationOrchestrator(
        model_name=args.model,
        headed=is_headed,
        slowmo=args.slowmo,
        max_healing_attempts=args.max_healing,
    )


    console.print("\n[bold cyan]Starting Autonomous Execution Pipeline...[/bold cyan]\n")

    try:
        run_data = await orchestrator.run(
            url=args.url,
            scenario=args.scenario,
            progress_callback=handle_progress,
        )
    except Exception as e:
        console.print(f"\n[bold red]Execution error:[/bold red] {str(e)}")
        return 1

    # Render Final Rich Progress Table
    console.print("\n")
    table = Table(title="Execution Pipeline Lifecycle", border_style="cyan", show_lines=True)
    table.add_column("Phase / Step", style="bold cyan", no_wrap=True)
    table.add_column("Final Status", style="bold", justify="center")
    table.add_column("Details & Output", style="white")

    for step, status, details in events:
        table.add_row(step, status_style(status), details)

    console.print(table)

    # Render Summary Panel
    success = run_data.get("success", False)
    summary_text = Text()

    if success:
        border_col = "green"
        summary_text.append("🎉 TEST SUITE PASSED SUCCESSFULLY!\n\n", style="bold green")
    else:
        border_col = "red"
        summary_text.append("❌ TEST SUITE FAILED AFTER HEALING ATTEMPTS\n\n", style="bold red")

    summary_text.append(f"• Total Execution Attempts: {run_data.get('attempts', 1)}\n", style="bold")
    summary_text.append(f"• Healing Iterations:       {len(run_data.get('healing_history', []))}\n")
    summary_text.append(f"• Page Object:             {run_data.get('page_file', 'N/A')}\n")
    summary_text.append(f"• Pytest Test File:        {run_data.get('test_file', 'N/A')}\n")
    summary_text.append(f"• HTML Report:             {run_data.get('html_report', 'N/A')}\n")
    summary_text.append(f"• Allure Results:          {run_data.get('allure_results', 'N/A')}\n")
    summary_text.append(f"• Executive Summary:       {run_data.get('summary_file', 'N/A')}\n")

    if not success and run_data.get("failure_reason"):
        summary_text.append(f"\nLast Failure Root Cause:\n{run_data.get('failure_reason')}", style="bold red")

    console.print("\n")
    console.print(Panel(summary_text, title="Final Execution Report", border_style=border_col))

    # Trigger allure serve if requested
    if args.serve_report:
        allure_bin = shutil.which("allure")
        allure_dir = run_data.get("allure_results") or f"reports/allure-results/{run_data.get('domain_name', '')}"
        if not allure_bin:
            console.print(
                f"\n[bold yellow]⚠️  Allure CLI ('allure') is not installed or not found in system PATH.[/bold yellow]\n"
                f"[dim]Skipping 'allure serve'. To view Allure reports interactively, install Allure CLI "
                f"(e.g. via Scoop: 'scoop install allure' or npm: 'npm install -g allure-commandline').[/dim]\n"
                f"[dim]Domain results stored in: [bold cyan]{allure_dir}[/bold cyan][/dim]\n"
            )
        else:
            console.print(f"\n[bold cyan]🚀 Serving Allure test report from {allure_dir}...[/bold cyan]")
            try:
                orchestrator.serve_report(run_data)
            except KeyboardInterrupt:
                console.print("\n[dim]Allure server closed.[/dim]")
            except Exception as e:
                console.print(f"\n[bold red]Error launching allure serve:[/bold red] {e}")

    return 0 if success else 1


def main() -> None:
    exit_code = asyncio.run(main_async())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
