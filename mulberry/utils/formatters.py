"""Utility functions for formatting numbers, currencies, and percentages"""

from typing import Optional


def format_currency(value: Optional[float], decimals: int = 2) -> str:
    """
    Format number as currency with $ symbol

    Args:
        value: Numeric value to format
        decimals: Number of decimal places

    Returns:
        Formatted string (e.g., "$1,234.56")
    """
    if value is None:
        return "N/A"

    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    elif abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    elif abs(value) >= 1_000:
        return f"${value / 1_000:.2f}K"
    else:
        return f"${value:,.{decimals}f}"


def format_percent(value: Optional[float], decimals: int = 2) -> str:
    """
    Format number as percentage

    Args:
        value: Decimal value (0.15 = 15%)
        decimals: Number of decimal places

    Returns:
        Formatted string (e.g., "15.00%")
    """
    if value is None:
        return "N/A"

    return f"{value * 100:.{decimals}f}%"


def format_number(value: Optional[float], decimals: int = 2) -> str:
    """
    Format number with thousands separators

    Args:
        value: Numeric value to format
        decimals: Number of decimal places

    Returns:
        Formatted string (e.g., "1,234.56")
    """
    if value is None:
        return "N/A"

    return f"{value:,.{decimals}f}"


def format_large_number(value: Optional[float]) -> str:
    """
    Format large numbers with K/M/B suffixes

    Args:
        value: Numeric value to format

    Returns:
        Formatted string (e.g., "1.23B")
    """
    if value is None:
        return "N/A"

    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    elif abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    elif abs(value) >= 1_000:
        return f"{value / 1_000:.2f}K"
    else:
        return f"{value:.2f}"


def format_ratio(value: Optional[float], decimals: int = 2) -> str:
    """
    Format ratio values (e.g., P/E, debt/equity)

    Args:
        value: Ratio value
        decimals: Number of decimal places

    Returns:
        Formatted string
    """
    if value is None:
        return "N/A"

    return f"{value:.{decimals}f}"
