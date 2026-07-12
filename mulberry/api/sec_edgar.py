"""SEC EDGAR client.

Fetches company filings and structured XBRL facts from the SEC's free EDGAR
APIs. No API key is required — SEC only asks for a descriptive ``User-Agent``
with contact info (supplied via ``config.sec_user_agent``) and a request rate at
or below 10 requests/second.

Every method degrades gracefully: on any network or parse error it logs a
warning and returns ``None``/empty, so the analysis pipeline can treat SEC data
as optional context and continue without it.

Endpoints (verified against live EDGAR):
- ticker→CIK map:  https://www.sec.gov/files/company_tickers.json
- recent filings:  https://data.sec.gov/submissions/CIK##########.json
- XBRL facts:      https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json
- filing document: https://www.sec.gov/Archives/edgar/data/<cik>/<accession>/<doc>
"""

import time
from typing import Optional, Dict, Any

import requests

from ..utils.logger import get_logger
from ..utils.config import config

logger = get_logger(__name__)


class SECEdgarClient:
    """Thin, rate-limited HTTP client for the SEC EDGAR APIs."""

    TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
    SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
    FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession}/{doc}"

    # SEC allows up to 10 req/s; stay just under with ~9 req/s.
    MIN_INTERVAL = 0.11

    # A user agent still on the placeholder default — SEC etiquette asks for a
    # real contact string.
    PLACEHOLDER_UA = "FinancialAnalysis contact@example.com"

    def __init__(self, user_agent: Optional[str] = None, session=None, timeout: int = 15):
        self.user_agent = user_agent or config.sec_user_agent
        self.session = session or requests.Session()
        self.timeout = timeout
        self._last_request = 0.0
        self._ticker_map: Optional[Dict[str, int]] = None

    # ------------------------------------------------------------------
    # Low-level HTTP (single choke point — monkeypatched in tests)
    # ------------------------------------------------------------------

    def _throttle(self) -> None:
        wait = self.MIN_INTERVAL - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()

    def _request(self, url: str) -> requests.Response:
        self._throttle()
        resp = self.session.get(
            url, headers={"User-Agent": self.user_agent}, timeout=self.timeout
        )
        resp.raise_for_status()
        return resp

    def _fetch_json(self, url: str) -> Any:
        return self._request(url).json()

    def _fetch_text(self, url: str) -> str:
        return self._request(url).text

    @property
    def using_placeholder_user_agent(self) -> bool:
        return self.user_agent.strip() == self.PLACEHOLDER_UA

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve_cik(self, ticker: str) -> Optional[str]:
        """Return the zero-padded 10-digit CIK for a ticker, or None."""
        try:
            if self._ticker_map is None:
                data = self._fetch_json(self.TICKERS_URL)
                self._ticker_map = {
                    row["ticker"].upper(): row["cik_str"] for row in data.values()
                }
            cik = self._ticker_map.get(ticker.upper())
            if cik is None:
                logger.debug(f"No CIK found for {ticker}")
                return None
            return str(cik).zfill(10)
        except Exception as e:
            logger.warning(f"CIK resolution failed for {ticker}: {e}")
            return None

    def get_submissions(self, cik: str) -> Optional[Dict[str, Any]]:
        """Recent-filings metadata for a CIK, or None."""
        try:
            return self._fetch_json(self.SUBMISSIONS_URL.format(cik=cik))
        except Exception as e:
            logger.warning(f"Submissions fetch failed for CIK {cik}: {e}")
            return None

    def get_company_facts(self, cik: str) -> Optional[Dict[str, Any]]:
        """All XBRL company facts for a CIK, or None."""
        try:
            return self._fetch_json(self.FACTS_URL.format(cik=cik))
        except Exception as e:
            logger.warning(f"Company facts fetch failed for CIK {cik}: {e}")
            return None

    def get_filing_document(
        self, cik: str, accession: str, primary_document: str
    ) -> Optional[str]:
        """Fetch a filing's primary document (HTML/text), or None."""
        try:
            acc = accession.replace("-", "")
            url = self.ARCHIVE_URL.format(
                cik_int=int(cik), accession=acc, doc=primary_document
            )
            return self._fetch_text(url)
        except Exception as e:
            logger.warning(
                f"Filing document fetch failed (CIK {cik}, {accession}): {e}"
            )
            return None
