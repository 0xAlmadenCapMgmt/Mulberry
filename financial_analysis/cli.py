"""Command-line interface for Charlotte - Financial Analysis App"""

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
    """Display Charlotte banner"""
    banner = """
 ██████╗██╗  ██╗ █████╗ ██████╗ ██╗      ██████╗ ████████╗████████╗███████╗
██╔════╝██║  ██║██╔══██╗██╔══██╗██║     ██╔═══██╗╚══██╔══╝╚══██╔══╝██╔════╝
██║     ███████║███████║██████╔╝██║     ██║   ██║   ██║      ██║   █████╗
██║     ██╔══██║██╔══██║██╔══██╗██║     ██║   ██║   ██║      ██║   ██╔══╝
╚██████╗██║  ██║██║  ██║██║  ██║███████╗╚██████╔╝   ██║      ██║   ███████╗
 ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝ ╚═════╝    ╚═╝      ╚═╝   ╚══════╝
    """

    subtitle = Text()
    subtitle.append("Ben Graham Value Investing Analysis\n", style="cyan")
    subtitle.append("Professional Reports • Interactive Charts • Deep Value Discovery", style="dim")

    console.print(banner, style="bold blue")
    console.print(subtitle, justify="center")
    console.print()


def run_async(coro):
    """Helper to run async functions in Click commands"""
    return asyncio.run(coro)


@click.group()
@click.version_option(version='0.1.0', prog_name='Charlotte')
def cli():
    """
    Charlotte - Financial Analysis Report Generator

    Ben Graham value investing analysis with professional HTML reports.

    \b
    Examples:
        fa graham-valuation AAPL
        fa graham-valuation INTC -o my_report.html
        fa clear-cache
    """
    # Validate configuration
    is_valid, errors = config.validate()
    if not is_valid:
        console.print("[bold red]Configuration Error:[/bold red]")
        for error in errors:
            console.print(f"  • {error}")
        console.print("\n[yellow]Please check your config/.env file[/yellow]")
        console.print("Run: [cyan]cp config/.env.example config/.env[/cyan]")
        raise click.Abort()


@cli.command()
@click.argument('symbol')
@click.option('--output', '-o', help='Output file path (default: auto-generated)')
@click.option('--open-browser', '-b', is_flag=True, help='Open report in browser after generation')
def graham_valuation(symbol: str, output: str, open_browser: bool):
    """
    Analyze stock using Ben Graham's valuation methods

    Generates comprehensive HTML report with:
    - Four Graham valuation methods
    - Margin of safety analysis
    - Defensive investor checklist
    - Interactive charts and visualizations

    \b
    Example:
        fa graham-valuation AAPL
        fa graham-valuation MSFT -o msft_analysis.html -b
    """
    # Show Charlotte banner
    show_banner()

    # Validate ticker
    is_valid, error = validate_ticker(symbol)
    if not is_valid:
        console.print(f"[bold red]Error:[/bold red] {error}")
        raise click.Abort()

    symbol = normalize_ticker(symbol)

    console.print(Panel(
        f"[bold cyan]Graham Deep Value Analysis[/bold cyan]\n"
        f"Symbol: [bold]{symbol}[/bold]",
        title="Charlotte Analysis",
        border_style="cyan"
    ))

    # Initialize generator
    cache_manager = CacheManager(str(config.cache_db_path))
    generator = ReportGenerator(cache_manager)

    # Generate report with progress indicator
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:

        task = progress.add_task("[cyan]Fetching data from APIs...", total=None)

        async def generate():
            try:
                # Update progress
                progress.update(task, description="[cyan]Analyzing fundamentals...")

                # Generate report
                report_path = await generator.generate_graham_report(symbol, output)

                progress.update(task, description="[green]✓ Analysis complete!")

                return report_path

            except Exception as e:
                progress.update(task, description=f"[red]✗ Error: {str(e)}")
                raise

        try:
            report_path = run_async(generate())

            # Display results
            console.print()
            console.print("[bold green]✓ Report generated successfully![/bold green]")
            console.print(f"[cyan]Location:[/cyan] {report_path}")

            # Open in browser if requested
            if open_browser:
                import webbrowser
                webbrowser.open(f"file://{Path(report_path).absolute()}")
                console.print("[green]✓ Opened in browser[/green]")

        except Exception as e:
            console.print(f"\n[bold red]✗ Analysis failed:[/bold red] {str(e)}")
            logger.error(f"Graham valuation failed: {e}", exc_info=True)
            raise click.Abort()


@cli.command()
@click.option('--all', '-a', 'clear_all', is_flag=True, help='Clear all cache (including valid entries)')
def clear_cache(clear_all: bool):
    """
    Clear expired cache entries

    By default, removes only expired entries.
    Use --all to clear entire cache.

    \b
    Example:
        fa clear-cache           # Clear expired only
        fa clear-cache --all     # Clear everything
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
            console.print("\n[green]✓ Entire cache cleared successfully[/green]")
        else:
            cache_manager.clear_expired()
            progress.update(task, description="[green]✓ Expired entries removed")
            console.print("\n[green]✓ Expired cache entries removed[/green]")


@cli.command()
def info():
    """
    Display configuration and system information
    """
    show_banner()

    table = Table(title="Charlotte Configuration", show_header=True)
    table.add_column("Setting", style="cyan", width=30)
    table.add_column("Value", style="white")

    # API Keys (masked)
    av_key = config.alpha_vantage_api_key
    av_masked = f"{av_key[:4]}...{av_key[-4:]}" if len(av_key) > 8 else "Not set"

    fmp_key = config.fmp_api_key
    fmp_masked = f"{fmp_key[:4]}...{fmp_key[-4:]}" if len(fmp_key) > 8 else "Not set"

    table.add_row("Alpha Vantage API Key", av_masked)
    table.add_row("FMP API Key", fmp_masked if fmp_key else "Not set")
    table.add_row("SEC User-Agent", config.sec_user_agent)
    table.add_row("", "")

    # Cache settings
    table.add_row("Cache Database", str(config.cache_db_path))
    table.add_row("Quote Cache TTL", f"{config.cache_ttl_quotes}s")
    table.add_row("Fundamentals Cache TTL", f"{config.cache_ttl_fundamentals}s")
    table.add_row("", "")

    # Paths
    table.add_row("Output Directory", str(config.output_dir))
    table.add_row("Templates Directory", str(config.templates_dir))

    console.print(table)

    # Validation status
    is_valid, errors = config.validate()
    if is_valid:
        console.print("\n[green]✓ Configuration is valid[/green]")
    else:
        console.print("\n[red]✗ Configuration errors:[/red]")
        for error in errors:
            console.print(f"  • {error}")


@cli.command()
@click.argument('api', type=click.Choice(['alpha-vantage', 'yahoo', 'all'], case_sensitive=False))
def test_api(api: str):
    """
    Test API connectivity

    \b
    Example:
        fa test-api alpha-vantage
        fa test-api all
    """
    show_banner()

    console.print(Panel(
        f"[bold cyan]Testing API Connectivity[/bold cyan]\n"
        f"API: [bold]{api}[/bold]",
        title="Charlotte API Test",
        border_style="cyan"
    ))

    async def test_alpha_vantage():
        from .api.alpha_vantage import AlphaVantageAPI
        try:
            api_client = AlphaVantageAPI()
            quote = await api_client.get_quote('AAPL')
            await api_client.close()
            return True, f"Connected - Latest AAPL price: ${quote['price']:.2f}"
        except Exception as e:
            return False, str(e)

    def test_yahoo():
        from .api.yahoo_finance import YahooFinanceAPI
        try:
            api_client = YahooFinanceAPI()
            info = api_client.get_info('AAPL')
            return True, f"Connected - {info['name']}"
        except Exception as e:
            return False, str(e)

    tests = []
    if api == 'all' or api == 'alpha-vantage':
        tests.append(('Alpha Vantage', test_alpha_vantage))
    if api == 'all' or api == 'yahoo':
        tests.append(('Yahoo Finance', lambda: test_yahoo()))

    for name, test_func in tests:
        console.print(f"\n[cyan]Testing {name}...[/cyan]")

        try:
            if asyncio.iscoroutinefunction(test_func):
                success, message = run_async(test_func())
            else:
                success, message = test_func()

            if success:
                console.print(f"[green]✓ {name}: {message}[/green]")
            else:
                console.print(f"[red]✗ {name}: {message}[/red]")

        except Exception as e:
            console.print(f"[red]✗ {name}: {str(e)}[/red]")


@cli.command()
def examples():
    """
    Show usage examples
    """
    show_banner()

    console.print(Panel(
        """
[bold cyan]Charlotte Usage Examples[/bold cyan]

[bold]1. Basic Graham Analysis:[/bold]
   [green]fa graham-valuation AAPL[/green]
   Generates comprehensive Graham valuation report for Apple

[bold]2. Custom Output Path:[/bold]
   [green]fa graham-valuation MSFT -o reports/microsoft.html[/green]
   Saves report to specific location

[bold]3. Auto-Open in Browser:[/bold]
   [green]fa graham-valuation GOOGL -b[/green]
   Generates report and opens in default browser

[bold]4. Test API Connectivity:[/bold]
   [green]fa test-api alpha-vantage[/green]
   Verifies Alpha Vantage API is working

[bold]5. Clear Expired Cache:[/bold]
   [green]fa clear-cache[/green]
   Removes expired cache entries to save space

[bold]6. View Configuration:[/bold]
   [green]fa info[/green]
   Displays current configuration settings

[bold]7. Multiple Analyses:[/bold]
   [green]for ticker in AAPL MSFT GOOGL; do fa graham-valuation $ticker; done[/green]
   Batch analyze multiple stocks
        """,
        title="Examples",
        border_style="cyan"
    ))


if __name__ == '__main__':
    cli()
