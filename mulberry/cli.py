"""Command-line interface for Mulberry — Multi-Framework Stock Analysis"""

import click
import asyncio
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from pathlib import Path

from .reports.generator import ReportGenerator
from .core.composite import CompositeScorer
from .cache.raw_cache import RawDataCache
from .utils.config import config
from .utils.logger import get_logger
from .utils.validators import validate_ticker, normalize_ticker

console = Console()
logger = get_logger(__name__)


def show_banner():
    """Display Mulberry banner with ASCII berry sprig"""
    banner_lines = [
        "███╗   ███╗██╗   ██╗██╗     ██████╗ ███████╗██████╗ ██████╗ ██╗   ██╗",
        "████╗ ████║██║   ██║██║     ██╔══██╗██╔════╝██╔══██╗██╔══██╗╚██╗ ██╔╝",
        "██╔████╔██║██║   ██║██║     ██████╔╝█████╗  ██████╔╝██████╔╝ ╚████╔╝ ",
        "██║╚██╔╝██║██║   ██║██║     ██╔══██╗██╔══╝  ██╔══██╗██╔══██╗  ╚██╔╝  ",
        "██║ ╚═╝ ██║╚██████╔╝███████╗██████╔╝███████╗██║  ██║██║  ██║   ██║   ",
        "╚═╝     ╚═╝ ╚═════╝ ╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ",
    ]

    berry_lines = [
        "   _/   ",
        "  (@)_  ",
        " (@)(@) ",
        "  (@)(@)",
        "   (@)  ",
        "        ",
    ]

    console.print()
    for bl, rl in zip(banner_lines, berry_lines):
        line = Text()
        line.append(bl, style="bold magenta")
        line.append("  " + rl, style="bold purple")
        console.print(line)

    subtitle = Text()
    subtitle.append("\nMulti-Framework Stock Analysis\n", style="cyan")
    subtitle.append("Value  •  Quality  •  Growth  •  Dividend  •  Momentum", style="dim")

    console.print(subtitle, justify="center")
    console.print()


def run_async(coro):
    return asyncio.run(coro)


@click.group()
@click.version_option(version='0.9.0', prog_name='Mulberry')
def cli():
    """
    Mulberry — Multi-Framework Stock Analysis

    Generates professional analysis reports using Yahoo Finance data,
    blending value, quality, growth, dividend, and momentum frameworks.

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
@click.option('--peers', '-p', help='Comma-separated peer tickers for relative comparison (e.g. PEP,KDP,MNST)')
@click.option('--profile', type=click.Choice(list(CompositeScorer.PROFILES)), default='balanced',
              show_default=True, help='Investor-style weighting profile')
@click.option('--filings/--no-filings', default=True, show_default=True,
              help='Include SEC EDGAR filing context (trends, red flags, excerpts)')
@click.option('--thesis/--no-thesis', default=True, show_default=True,
              help='Include an AI-generated thesis narrative (needs ANTHROPIC_API_KEY; skipped without one)')
def analyze(symbol: str, output: str, open_browser: bool, peers: str, profile: str,
            filings: bool, thesis: bool):
    """
    Analyze a stock and generate an HTML analysis report.

    Blends six intrinsic value methods with quality, growth, dividend,
    and momentum frameworks into a composite score, rendered with
    interactive Plotly charts.

    \b
    Example:
        fa analyze AAPL
        fa analyze MSFT -o msft_report.html -b
        fa analyze KO --peers PEP,KDP,MNST --profile income
    """
    show_banner()

    is_valid, error = validate_ticker(symbol)
    if not is_valid:
        console.print(f"[bold red]Error:[/bold red] {error}")
        raise click.Abort()

    symbol = normalize_ticker(symbol)
    peer_list = [p.strip().upper() for p in peers.split(',') if p.strip()] if peers else None

    detail = f"Symbol: [bold]{symbol}[/bold]\nProfile: [bold]{profile}[/bold]"
    if peer_list:
        detail += f"\nPeers: [bold]{', '.join(peer_list)}[/bold]"
    console.print(Panel(
        f"[bold cyan]Multi-Framework Analysis[/bold cyan]\n{detail}",
        title="Mulberry",
        border_style="cyan"
    ))

    if filings and config.sec_user_agent.strip() == 'FinancialAnalysis contact@example.com':
        console.print(
            "[yellow]Tip:[/yellow] set [bold]SEC_USER_AGENT[/bold] in config/.env to a real "
            "contact string (SEC etiquette for EDGAR requests)."
        )

    generator = ReportGenerator(profile=profile)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Fetching data from Yahoo Finance...", total=None)

        async def generate():
            try:
                progress.update(task, description="[cyan]Running valuation analysis...")
                report_path = await generator.generate_report(
                    symbol, output, peers=peer_list, include_filings=filings,
                    include_thesis=thesis,
                )
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
@click.argument('symbols', nargs=-1)
@click.option('--universe', '-u', type=click.Path(exists=True),
              help='File with one ticker per line (used in addition to SYMBOLS)')
@click.option('--output', '-o', help='Output HTML path (CSV written alongside)')
@click.option('--open-browser', '-b', is_flag=True, help='Open the screen in a browser')
@click.option('--profile', type=click.Choice(list(CompositeScorer.PROFILES)), default='balanced',
              show_default=True, help='Investor-style weighting profile')
@click.option('--filings/--no-filings', default=False, show_default=True,
              help='Add SEC filing columns (red flags, leverage trend) — slower')
def screen(symbols, universe, output, open_browser, profile, filings):
    """
    Screen a universe of tickers, ranked by composite score.

    Produces a ranked HTML comparison plus a CSV alongside it.

    \b
    Example:
        fa screen AAPL MSFT KO PLTR
        fa screen --universe watchlist.txt --profile deep_value
        fa screen AAPL MSFT --filings
    """
    show_banner()

    tickers = [s.upper() for s in symbols]
    if universe:
        with open(universe, encoding='utf-8') as f:
            tickers += [line.strip().upper() for line in f
                        if line.strip() and not line.startswith('#')]
    if not tickers:
        console.print("[bold red]Error:[/bold red] provide tickers or --universe FILE")
        raise click.Abort()

    for t in tickers:
        ok, err = validate_ticker(t)
        if not ok:
            console.print(f"[bold red]Error:[/bold red] {t}: {err}")
            raise click.Abort()

    console.print(Panel(
        f"[bold cyan]Universe Screen[/bold cyan]\n"
        f"Tickers: [bold]{len(tickers)}[/bold]\n"
        f"Profile: [bold]{profile}[/bold]"
        + ("\nFilings columns: [bold]on[/bold]" if filings else ""),
        title="Mulberry",
        border_style="cyan"
    ))

    from .reports.screen import ScreenReportGenerator
    generator = ScreenReportGenerator(profile=profile, include_filings=filings)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(
            f"[cyan]Analyzing {len(tickers)} tickers...", total=None)
        try:
            report_path = run_async(generator.generate(tickers, output))
            progress.update(task, description="[green]✓ Screen ready!")
        except Exception as e:
            progress.update(task, description=f"[red]✗ {str(e)}")
            console.print(f"\n[bold red]✗ Screen failed:[/bold red] {str(e)}")
            logger.error(f"Screen failed: {e}", exc_info=True)
            raise click.Abort()

    console.print()
    console.print("[bold green]✓ Screen generated![/bold green]")
    console.print(f"[cyan]HTML:[/cyan] {report_path}")
    console.print(f"[cyan]CSV:[/cyan]  {str(Path(report_path).with_suffix('.csv'))}")

    if open_browser:
        import webbrowser
        webbrowser.open(f"file://{Path(report_path).absolute()}")
        console.print("[green]✓ Opened in browser[/green]")


@cli.command()
@click.option('--host', default='127.0.0.1', show_default=True, help='Interface to bind')
@click.option('--port', default=8000, show_default=True, type=int, help='Port to listen on')
@click.option('--reload', is_flag=True, help='Auto-reload on code changes (development)')
def serve(host: str, port: int, reload: bool):
    """
    Launch the Mulberry web front end.

    A local browser UI over the same analysis pipeline: a ticker search box,
    profile/peers/filings controls, a universe screener, and a report history
    browser.

    \b
    Example:
        fa serve
        fa serve --host 0.0.0.0 --port 9000
    """
    show_banner()
    console.print(Panel(
        f"[bold cyan]Mulberry Web[/bold cyan]\n"
        f"Open [bold]http://{host}:{port}[/bold] in your browser\n"
        f"[dim]Ctrl+C to stop[/dim]",
        title="Mulberry",
        border_style="cyan"
    ))
    try:
        import uvicorn
    except ImportError:
        console.print("[bold red]Error:[/bold red] web dependencies not installed. "
                      "Run [bold]pip install 'mulberry[web]'[/bold] or "
                      "[bold]pip install fastapi uvicorn python-multipart[/bold].")
        raise click.Abort()

    # Import target string keeps --reload working (uvicorn re-imports the app).
    uvicorn.run("mulberry.web.app:create_app", factory=True,
                host=host, port=port, reload=reload)


@cli.command()
def clear_cache():
    """
    Clear cached ticker data so the next run fetches fresh from Yahoo.
    """
    raw_cache = RawDataCache(config.cache_dir, config.cache_ttl_fundamentals)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Clearing cache...", total=None)
        removed = raw_cache.clear()
        progress.update(task, description="[green]✓ Cache cleared")
        console.print(
            f"\n[green]✓ Cache cleared[/green] "
            f"([cyan]{removed}[/cyan] cached tickers removed)"
        )


@cli.command()
def info():
    """Display configuration and paths."""
    show_banner()

    table = Table(title="Mulberry Configuration", show_header=True)
    table.add_column("Setting", style="cyan", width=30)
    table.add_column("Value", style="white")

    table.add_row("Cache Directory", str(config.cache_dir / "raw"))
    table.add_row("Cache TTL", f"{config.cache_ttl_fundamentals}s")
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
        title="Mulberry",
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
[bold cyan]Mulberry Usage Examples[/bold cyan]

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
