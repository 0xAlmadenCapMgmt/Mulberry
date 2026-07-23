"""Web front end (FastAPI) — a thin presentation layer over the analysis pipeline.

No scoring logic lives here; every route reuses ReportGenerator /
ScreenReportGenerator and serves the HTML/CSV artifacts they already produce.
"""

from .app import create_app

__all__ = ["create_app"]
