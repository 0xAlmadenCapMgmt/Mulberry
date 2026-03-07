"""SQLAlchemy models for cache database"""

from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class QuoteCache(Base):
    """Cache for real-time stock quotes"""
    __tablename__ = 'quotes_cache'

    symbol = Column(String(10), primary_key=True)
    price = Column(String(50))
    data_json = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ttl = Column(Integer, default=300)  # 5 minutes

    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        if not self.timestamp:
            return True
        elapsed = (datetime.utcnow() - self.timestamp).total_seconds()
        return elapsed > self.ttl


class FundamentalsCache(Base):
    """Cache for fundamental data (income statements, balance sheets, etc.)"""
    __tablename__ = 'fundamentals_cache'

    cache_key = Column(String(100), primary_key=True)
    symbol = Column(String(10), index=True)
    data_type = Column(String(50))  # 'overview', 'income', 'balance', etc.
    data_json = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ttl = Column(Integer, default=86400)  # 24 hours

    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        if not self.timestamp:
            return True
        elapsed = (datetime.utcnow() - self.timestamp).total_seconds()
        return elapsed > self.ttl


class FilingsCache(Base):
    """Cache for SEC filings data"""
    __tablename__ = 'filings_cache'

    cache_key = Column(String(100), primary_key=True)
    symbol = Column(String(10), index=True)
    cik = Column(String(10))
    form_type = Column(String(10))  # '10-K', '10-Q', etc.
    data_json = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ttl = Column(Integer, default=604800)  # 7 days

    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        if not self.timestamp:
            return True
        elapsed = (datetime.utcnow() - self.timestamp).total_seconds()
        return elapsed > self.ttl


def create_cache_db(db_path: str):
    """Create cache database with all tables"""
    engine = create_engine(f'sqlite:///{db_path}')
    Base.metadata.create_all(engine)
    return engine
