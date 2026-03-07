"""Configuration manager for loading environment variables and settings"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


class Config:
    """Application configuration loaded from .env file"""

    _instance: Optional['Config'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """Load configuration from .env file"""
        # Find .env file in config directory
        project_root = Path(__file__).parent.parent.parent
        env_path = project_root / "config" / ".env"

        if env_path.exists():
            load_dotenv(env_path)
        else:
            # Try loading from current directory
            load_dotenv()

        # API Keys
        self.alpha_vantage_api_key = os.getenv('ALPHA_VANTAGE_API_KEY', '')
        self.fmp_api_key = os.getenv('FMP_API_KEY', '')
        self.sec_user_agent = os.getenv('SEC_USER_AGENT', 'FinancialAnalysis contact@example.com')

        # Cache settings (in seconds)
        self.cache_ttl_quotes = int(os.getenv('CACHE_TTL_QUOTES', '300'))
        self.cache_ttl_fundamentals = int(os.getenv('CACHE_TTL_FUNDAMENTALS', '86400'))
        self.cache_ttl_filings = int(os.getenv('CACHE_TTL_FILINGS', '604800'))

        # Rate limits (requests per minute)
        self.alpha_vantage_rate_limit = int(os.getenv('ALPHA_VANTAGE_RATE_LIMIT', '5'))
        self.fmp_rate_limit = int(os.getenv('FMP_RATE_LIMIT', '300'))
        self.sec_rate_limit = int(os.getenv('SEC_RATE_LIMIT', '10'))

        # Paths
        self.project_root = project_root
        self.output_dir = project_root / "output" / "reports"
        self.cache_dir = project_root / ".cache"
        self.templates_dir = project_root / "financial_analysis" / "templates"

        # Ensure directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def validate(self) -> tuple[bool, list[str]]:
        """Validate configuration and return (is_valid, error_messages)"""
        errors = []

        if not self.alpha_vantage_api_key:
            errors.append("ALPHA_VANTAGE_API_KEY not set in .env file")

        if not self.sec_user_agent or 'example.com' in self.sec_user_agent:
            errors.append("SEC_USER_AGENT must be set with real contact email")

        return (len(errors) == 0, errors)

    @property
    def cache_db_path(self) -> Path:
        """Path to SQLite cache database"""
        return self.cache_dir / "cache.db"


# Singleton instance
config = Config()
