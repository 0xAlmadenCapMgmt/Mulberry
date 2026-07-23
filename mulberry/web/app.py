"""FastAPI application for Mulberry.

Routes:
  GET  /                 home — analyze form + recent reports
  POST /analyze          run a single-name analysis, redirect to the report
  GET  /screen           universe-screen form
  POST /screen           run a screen, redirect to the ranked report
  GET  /reports          report history browser
  GET  /reports/{name}   serve a generated HTML/CSV artifact (path-safe)
  GET  /health           liveness probe

The front end is a presentation layer only — it calls the same
ReportGenerator / ScreenReportGenerator the CLI uses and serves the artifacts
they write to the output directory.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ..core.composite import CompositeScorer
from ..reports.generator import ReportGenerator
from ..reports.screen import ScreenReportGenerator
from ..utils.config import config
from ..utils.logger import get_logger
from ..utils.validators import validate_ticker, normalize_ticker

logger = get_logger(__name__)

_WEB_DIR = Path(__file__).parent
_SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+\.(html|csv)$")


def _safe_report_path(filename: str) -> Path:
    """Resolve a report filename inside output_dir, or raise 404.

    Guards against path traversal — only plain .html/.csv names that resolve
    to a direct child of the output directory are allowed.
    """
    if not _SAFE_NAME.match(filename):
        raise HTTPException(status_code=404, detail="Not found")
    out = config.output_dir.resolve()
    path = (out / filename).resolve()
    if path.parent != out or not path.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return path


def _recent_reports(limit: int = 25) -> List[dict]:
    """List generated HTML reports, newest first."""
    out = config.output_dir
    if not out.exists():
        return []
    reports = []
    for path in out.glob("*.html"):
        name = path.name
        kind = "screen" if name.startswith("screen_") else "analysis"
        symbol = ""
        if kind == "analysis":
            m = re.match(r"analysis_([A-Za-z0-9.\-]+)_", name)
            symbol = m.group(1) if m else ""
        reports.append({
            "filename": name,
            "kind": kind,
            "symbol": symbol,
            "modified": datetime.fromtimestamp(path.stat().st_mtime),
            "has_csv": path.with_suffix(".csv").exists(),
        })
    reports.sort(key=lambda r: r["modified"], reverse=True)
    return reports[:limit]


def create_app(
    report_generator: Optional[ReportGenerator] = None,
    screen_generator_factory=None,
) -> FastAPI:
    """Build the FastAPI app. Generators are injectable for testing."""
    app = FastAPI(title="Mulberry", docs_url=None, redoc_url=None)
    templates = Jinja2Templates(directory=str(_WEB_DIR / "templates"))
    profiles = list(CompositeScorer.PROFILES)

    def _make_report_generator(profile: str) -> ReportGenerator:
        if report_generator is not None:
            return report_generator
        return ReportGenerator(profile=profile)

    def _make_screen_generator(profile: str, include_filings: bool) -> ScreenReportGenerator:
        if screen_generator_factory is not None:
            return screen_generator_factory(profile, include_filings)
        return ScreenReportGenerator(profile=profile, include_filings=include_filings)

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        return templates.TemplateResponse("home.html", {
            "request": request,
            "profiles": profiles,
            "reports": _recent_reports(10),
        })

    @app.post("/analyze")
    async def analyze(
        request: Request,
        symbol: str = Form(...),
        profile: str = Form("balanced"),
        peers: str = Form(""),
        filings: bool = Form(False),
        thesis: bool = Form(False),
    ):
        ok, err = validate_ticker(symbol)
        if not ok or profile not in CompositeScorer.PROFILES:
            return _error_page(templates, request, err or "Invalid profile", 400)

        symbol = normalize_ticker(symbol)
        peer_list = [p.strip().upper() for p in peers.split(",") if p.strip()] or None
        try:
            generator = _make_report_generator(profile)
            path = await generator.generate_report(
                symbol, peers=peer_list,
                include_filings=filings, include_thesis=thesis,
            )
        except Exception as e:
            logger.error(f"Web analyze failed for {symbol}: {e}", exc_info=True)
            return _error_page(templates, request, f"Analysis failed for {symbol}: {e}", 502)

        return RedirectResponse(url=f"/reports/{Path(path).name}", status_code=303)

    @app.get("/screen", response_class=HTMLResponse)
    async def screen_form(request: Request):
        return templates.TemplateResponse("screen.html", {
            "request": request, "profiles": profiles,
        })

    @app.post("/screen")
    async def run_screen(
        request: Request,
        symbols: str = Form(...),
        profile: str = Form("balanced"),
        filings: bool = Form(False),
    ):
        tickers = [t.strip().upper() for t in re.split(r"[,\s]+", symbols) if t.strip()]
        if not tickers or profile not in CompositeScorer.PROFILES:
            return _error_page(templates, request, "Enter at least one ticker", 400)
        for t in tickers:
            ok, err = validate_ticker(t)
            if not ok:
                return _error_page(templates, request, f"{t}: {err}", 400)

        try:
            generator = _make_screen_generator(profile, filings)
            path = await generator.generate(tickers)
        except Exception as e:
            logger.error(f"Web screen failed: {e}", exc_info=True)
            return _error_page(templates, request, f"Screen failed: {e}", 502)

        return RedirectResponse(url=f"/reports/{Path(path).name}", status_code=303)

    @app.get("/reports", response_class=HTMLResponse)
    async def reports(request: Request):
        return templates.TemplateResponse("history.html", {
            "request": request, "reports": _recent_reports(50),
        })

    @app.get("/reports/{filename}")
    async def serve_report(filename: str):
        path = _safe_report_path(filename)
        media = "text/csv" if path.suffix == ".csv" else "text/html"
        return FileResponse(path, media_type=media)

    @app.get("/health")
    async def health():
        return {"status": "ok", "reports": len(_recent_reports(9999))}

    return app


def _error_page(templates, request, message: str, status: int):
    return templates.TemplateResponse(
        "error.html", {"request": request, "message": message}, status_code=status,
    )
