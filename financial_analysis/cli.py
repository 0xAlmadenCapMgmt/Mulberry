"""Command-line interface for Charlotte - Financial Analysis"""

import click
import asyncio
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from pathlib import Path

from .reports.generator import ReportGenerator
from .cache.database import CacheManager
from .utils.config import config
from .utils.logger import get_logger
from .utils.validators import validate_ticker, normalize_ticker

console = Console()
logger = get_logger(__name__)


def show_banner():
    """Display Charlotte banner with ASCII rose"""
    banner_lines = [
        " ██████╗██╗  ██╗ █████╗ ██████╗ ██╗      ██████╗ ████████╗████████╗███████╗",
        "██╔════╝██║  ██║██╔══██╗██╔══██╗██║     ██╔═══██╗╚══██╔══╝╚══██╔══╝██╔════╝",
        "██║     ███████║███████║██████╔╝██║     ██║   ██║   ██║      ██║   █████╗   ",
        "██║     ██╔══██║██╔══██║██╔══██╗██║     ██║   ██║   ██║      ██║   ██╔══╝   ",
        "╚██████╗██║  ██║██║  ██║██║  ██║███████╗╚██████╔╝   ██║      ██║   ███████╗ ",
        " ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝ ╚═════╝    ╚═╝      ╚═╝   ╚══════╝",
    ]

    rose_lines = [
        "  ,---.  ",
        " /(@@@)\\ ",
        "| ( @ ) |",
        " \\(@@@)/ ",
        "  `---'  ",
        "    |    ",
    ]

    console.print()
    for bl, rl in zip(banner_lines, rose_lines):
        line = Text()
        line.append(bl, style="bold blue")
        line.append("  " + rl, style="bold red")
        console.print(line)

    subtitle = Text()
    subtitle.append("\nFundamental Value Analysis ", style="cyan")
    subtitle.append("♥\n", style="bold red")
    subtitle.append("Professional Reports  •  Interactive Charts  •  No API Key Required", style="dim")

    console.print(subtitle, justify="center")
    console.print()


def run_async(coro):
    return asyncio.run(coro)


@click.group()
@click.version_option(version='0.2.0', prog_name='Charlotte')
def cli():
    """
    Charlotte - Fundamental Financial Analysis

    Generates professional valuation reports using Yahoo Finance data.

    \b
    Examples:
        fa analyze AAPL
        fa analyze MSFT -o my_report.html -b
        fa clear-cache
    """
    is_valid, errors = config.validate()
    if not is_valid:
        console.print("[bold red]Configuration Error:[/bold red]")
        for error in errors:
            console.print(f"  • {error}")
        raise click.Abort()


@cli.command()
@click.argument('symbol')
@click.option('--output', '-o', help='Output file path (default: auto-generated)')
@click.option('--open-browser', '-b', is_flag=True, help='Open report in browser after generation')
def analyze(symbol: str, output: str, open_browser: bool):
    """
    Analyze a stock and generate an HTML valuation report.

    Uses four intrinsic value methods with margin of safety analysis,
    financial health scoring, and interactive Plotly charts.

    \b
    Example:
        fa analyze AAPL
        fa analyze MSFT -o msft_report.html -b
    """
    show_banner()

    is_valid, error = validate_ticker(symbol)
    if not is_valid:
        console.print(f"[bold red]Error:[/bold red] {error}")
        raise click.Abort()

    symbol = normalize_ticker(symbol)

    console.print(Panel(
        f"[bold cyan]Fundamental Value Analysis[/bold cyan]\n"
        f"Symbol: [bold]{symbol}[/bold]",
        title="Charlotte",
        border_style="cyan"
    ))

    cache_manager = CacheManager(str(config.cache_db_path))
    generator = ReportGenerator(cache_manager)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Fetching data from Yahoo Finance...", total=None)

        async def generate():
            try:
                progress.update(task, description="[cyan]Running valuation analysis...")
                report_path = await generator.generate_report(symbol, output)
                progress.update(task, description="[green]✓ Report ready!")
                return report_path
            except Exception as e:
                progress.update(task, description=f"[red]✗ {str(e)}")
                raise

        try:
            report_path = run_async(generate())
            console.print()
            console.print("[bold green]✓ Report generated successfully![/bold green]")
            console.print(f"[cyan]Location:[/cyan] {report_path}")

            if open_browser:
                import webbrowser
                webbrowser.open(f"file://{Path(report_path).absolute()}")
                console.print("[green]✓ Opened in browser[/green]")

        except Exception as e:
            console.print(f"\n[bold red]✗ Analysis failed:[/bold red] {str(e)}")
            logger.error(f"Analysis failed: {e}", exc_info=True)
            raise click.Abort()


@cli.command()
@click.option('--all', '-a', 'clear_all', is_flag=True, help='Clear all cache (including valid entries)')
def clear_cache(clear_all: bool):
    """
    Clear cache entries.

    By default removes only expired entries. Use --all to clear everything.
    """
    cache_manager = CacheManager(str(config.cache_db_path))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Clearing cache...", total=None)

        if clear_all:
            cache_manager.clear_all()
            progress.update(task, description="[green]✓ All cache cleared")
            console.print("\n[green]✓ Entire cache cleared[/green]")
        else:
            cache_manager.clear_expired()
            progress.update(task, description="[green]✓ Expired entries removed")
            console.print("\n[green]✓ Expired cache entries removed[/green]")


@cli.command()
def info():
    """Display configuration and paths."""
    show_banner()

    table = Table(title="Charlotte Configuration", show_header=True)
    table.add_column("Setting", style="cyan", width=30)
    table.add_column("Value", style="white")

    table.add_row("Cache Database", str(config.cache_db_path))
    table.add_row("Quote Cache TTL", f"{config.cache_ttl_quotes}s")
    table.add_row("Fundamentals Cache TTL", f"{config.cache_ttl_fundamentals}s")
    table.add_row("AAA Bond Yield (for valuation)", f"{config.aaa_bond_yield * 100:.1f}%")
    table.add_row("", "")
    table.add_row("Output Directory", str(config.output_dir))
    table.add_row("Templates Directory", str(config.templates_dir))

    console.print(table)
    console.print("\n[green]✓ Data source: Yahoo Finance (no API key required)[/green]")


@cli.command()
def test_api():
    """Test Yahoo Finance connectivity."""
    show_banner()

    console.print(Panel(
        "[bold cyan]Testing Yahoo Finance Connectivity[/bold cyan]",
        title="Charlotte",
        border_style="cyan"
    ))

    from .api.yahoo_finance import YahooFinanceAPI
    try:
        api = YahooFinanceAPI()
        info = api.get_info('AAPL')
        console.print(f"[green]✓ Yahoo Finance: Connected — {info['name']}[/green]")
    except Exception as e:
        console.print(f"[red]✗ Yahoo Finance: {str(e)}[/red]")


@cli.command()
def examples():
    """Show usage examples."""
    show_banner()

    console.print(Panel(
        """
[bold cyan]Charlotte Usage Examples[/bold cyan]

[bold]1. Basic Analysis:[/bold]
   [green]fa analyze AAPL[/green]
   Generates a full valuation report for Apple

[bold]2. Custom Output Path:[/bold]
   [green]fa analyze MSFT -o reports/microsoft.html[/green]
   Saves report to a specific location

[bold]3. Auto-Open in Browser:[/bold]
   [green]fa analyze GOOGL -b[/green]
   Generates report and opens it immediately

[bold]4. Test Data Connection:[/bold]
   [green]fa test-api[/green]
   Verifies Yahoo Finance is reachable

[bold]5. Clear Expired Cache:[/bold]
   [green]fa clear-cache[/green]
   Removes stale cached data

[bold]6. View Configuration:[/bold]
   [green]fa info[/green]
   Displays current settings and paths

[bold]7. Batch Analysis:[/bold]
   [green]for ticker in AAPL MSFT GOOGL; do fa analyze $ticker; done[/green]
   Analyze multiple stocks in sequence
        """,
        title="Examples",
        border_style="cyan"
    ))


if __name__ == '__main__':
    cli()
