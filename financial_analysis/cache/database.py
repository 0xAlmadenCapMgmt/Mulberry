"""Cache manager with SQLite backend - reused pattern from portfolio-tracker"""

import json
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path

from .models import Base, QuoteCache, FundamentalsCache, FilingsCache
from ..utils.logger import get_logger

logger = get_logger(__name__)


class CacheManager:
    """
    SQLite-based cache manager with TTL support
    Reused pattern from portfolio-tracker project
    """

    def __init__(self, db_path: str):
        """
        Initialize cache manager

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Create database engine and session
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

        logger.info(f"Cache initialized at {db_path}")

    def get_quote(self, symbol: str) -> Optional[dict]:
        """
        Retrieve cached quote data

        Args:
            symbol: Stock ticker symbol

        Returns:
            Cached data dict or None if expired/missing
        """
        session = self.Session()
        try:
            entry = session.query(QuoteCache).filter_by(symbol=symbol.upper()).first()

            if entry is None:
                logger.debug(f"Cache miss: {symbol} (quote)")
                return None

            if entry.is_expired():
                logger.debug(f"Cache expired: {symbol} (quote)")
                session.delete(entry)
                session.commit()
                return None

            logger.debug(f"Cache hit: {symbol} (quote)")
            return json.loads(entry.data_json)

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
        finally:
            session.close()

    def set_quote(self, symbol: str, data: dict, ttl: int = 300):
        """
        Store quote data in cache

        Args:
            symbol: Stock ticker symbol
            data: Data to cache
            ttl: Time to live in seconds (default 5 minutes)
        """
        session = self.Session()
        try:
            # Remove existing entry
            session.query(QuoteCache).filter_by(symbol=symbol.upper()).delete()

            # Create new entry
            entry = QuoteCache(
                symbol=symbol.upper(),
                price=str(data.get('price', '')),
                data_json=json.dumps(data),
                timestamp=datetime.utcnow(),
                ttl=ttl
            )
            session.add(entry)
            session.commit()
            logger.debug(f"Cached quote: {symbol}")

        except Exception as e:
            logger.error(f"Cache set error: {e}")
            session.rollback()
        finally:
            session.close()

    def get_fundamentals(self, symbol: str, data_type: str) -> Optional[dict]:
        """
        Retrieve cached fundamental data

        Args:
            symbol: Stock ticker symbol
            data_type: Type of data ('overview', 'income', 'balance', etc.)

        Returns:
            Cached data dict or None if expired/missing
        """
        cache_key = f"{symbol.upper()}:{data_type}"
        session = self.Session()
        try:
            entry = session.query(FundamentalsCache).filter_by(cache_key=cache_key).first()

            if entry is None:
                logger.debug(f"Cache miss: {cache_key}")
                return None

            if entry.is_expired():
                logger.debug(f"Cache expired: {cache_key}")
                session.delete(entry)
                session.commit()
                return None

            logger.debug(f"Cache hit: {cache_key}")
            return json.loads(entry.data_json)

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
        finally:
            session.close()

    def set_fundamentals(self, symbol: str, data_type: str, data: dict, ttl: int = 86400):
        """
        Store fundamental data in cache

        Args:
            symbol: Stock ticker symbol
            data_type: Type of data ('overview', 'income', 'balance', etc.)
            data: Data to cache
            ttl: Time to live in seconds (default 24 hours)
        """
        cache_key = f"{symbol.upper()}:{data_type}"
        session = self.Session()
        try:
            # Remove existing entry
            session.query(FundamentalsCache).filter_by(cache_key=cache_key).delete()

            # Create new entry
            entry = FundamentalsCache(
                cache_key=cache_key,
                symbol=symbol.upper(),
                data_type=data_type,
                data_json=json.dumps(data),
                timestamp=datetime.utcnow(),
                ttl=ttl
            )
            session.add(entry)
            session.commit()
            logger.debug(f"Cached fundamentals: {cache_key}")

        except Exception as e:
            logger.error(f"Cache set error: {e}")
            session.rollback()
        finally:
            session.close()

    def get_filing(self, symbol: str, form_type: str) -> Optional[dict]:
        """
        Retrieve cached SEC filing data

        Args:
            symbol: Stock ticker symbol
            form_type: Form type ('10-K', '10-Q', etc.)

        Returns:
            Cached data dict or None if expired/missing
        """
        cache_key = f"{symbol.upper()}:{form_type}"
        session = self.Session()
        try:
            entry = session.query(FilingsCache).filter_by(cache_key=cache_key).first()

            if entry is None:
                logger.debug(f"Cache miss: {cache_key}")
                return None

            if entry.is_expired():
                logger.debug(f"Cache expired: {cache_key}")
                session.delete(entry)
                session.commit()
                return None

            logger.debug(f"Cache hit: {cache_key}")
            return json.loads(entry.data_json)

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
        finally:
            session.close()

    def set_filing(self, symbol: str, cik: str, form_type: str, data: dict, ttl: int = 604800):
        """
        Store SEC filing data in cache

        Args:
            symbol: Stock ticker symbol
            cik: Company CIK number
            form_type: Form type ('10-K', '10-Q', etc.)
            data: Data to cache
            ttl: Time to live in seconds (default 7 days)
        """
        cache_key = f"{symbol.upper()}:{form_type}"
        session = self.Session()
        try:
            # Remove existing entry
            session.query(FilingsCache).filter_by(cache_key=cache_key).delete()

            # Create new entry
            entry = FilingsCache(
                cache_key=cache_key,
                symbol=symbol.upper(),
                cik=cik,
                form_type=form_type,
                data_json=json.dumps(data),
                timestamp=datetime.utcnow(),
                ttl=ttl
            )
            session.add(entry)
            session.commit()
            logger.debug(f"Cached filing: {cache_key}")

        except Exception as e:
            logger.error(f"Cache set error: {e}")
            session.rollback()
        finally:
            session.close()

    def clear_expired(self):
        """Remove all expired cache entries"""
        session = self.Session()
        try:
            # Clear expired quotes
            quotes = session.query(QuoteCache).all()
            expired_count = 0
            for quote in quotes:
                if quote.is_expired():
                    session.delete(quote)
                    expired_count += 1

            # Clear expired fundamentals
            fundamentals = session.query(FundamentalsCache).all()
            for fund in fundamentals:
                if fund.is_expired():
                    session.delete(fund)
                    expired_count += 1

            # Clear expired filings
            filings = session.query(FilingsCache).all()
            for filing in filings:
                if filing.is_expired():
                    session.delete(filing)
                    expired_count += 1

            session.commit()
            if expired_count > 0:
                logger.info(f"Cleared {expired_count} expired cache entries")

        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            session.rollback()
        finally:
            session.close()

    def clear_all(self):
        """Clear entire cache"""
        session = self.Session()
        try:
            session.query(QuoteCache).delete()
            session.query(FundamentalsCache).delete()
            session.query(FilingsCache).delete()
            session.commit()
            logger.info("Cache cleared")

        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            session.rollback()
        finally:
            session.close()
