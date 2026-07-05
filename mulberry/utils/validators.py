"""Data validation utilities"""

import re
from typing import Optional


def validate_ticker(ticker: str) -> tuple[bool, Optional[str]]:
    """
    Validate stock ticker symbol

    Args:
        ticker: Ticker symbol to validate

    Returns:
        (is_valid, error_message)
    """
    if not ticker:
        return False, "Ticker symbol cannot be empty"

    # Clean ticker
    ticker = ticker.strip().upper()

    # Basic validation: 1-5 alphanumeric characters
    if not re.match(r'^[A-Z]{1,5}$', ticker):
        return False, f"Invalid ticker format: {ticker}"

    return True, None


def validate_cik(cik: str) -> tuple[bool, Optional[str]]:
    """
    Validate SEC CIK number

    Args:
        cik: CIK number to validate

    Returns:
        (is_valid, error_message)
    """
    if not cik:
        return False, "CIK cannot be empty"

    # CIK should be numeric and 10 digits when padded
    cik = cik.strip()
    if not cik.isdigit():
        return False, f"CIK must be numeric: {cik}"

    return True, None


def normalize_ticker(ticker: str) -> str:
    """Normalize ticker symbol to uppercase"""
    return ticker.strip().upper()


def pad_cik(cik: str) -> str:
    """Pad CIK to 10 digits with leading zeros"""
    return cik.strip().zfill(10)
