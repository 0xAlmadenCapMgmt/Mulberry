"""Test API connectivity"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from financial_analysis.api.alpha_vantage import AlphaVantageAPI
from financial_analysis.api.yahoo_finance import YahooFinanceAPI
from financial_analysis.utils.config import config


async def test_alpha_vantage():
    """Test Alpha Vantage API"""
    print("\n=== Testing Alpha Vantage API ===")

    try:
        api = AlphaVantageAPI()
        print(f"API Key: {config.alpha_vantage_api_key[:8]}...")

        print("Fetching AAPL quote...")
        quote = await api.get_quote('AAPL')
        print(f"✓ Quote: ${quote['price']:.2f}")

        print("Fetching AAPL overview...")
        overview = await api.get_overview('AAPL')
        print(f"✓ Company: {overview.get('Name', 'N/A')}")

        await api.close()
        print("✓ Alpha Vantage API working correctly")
        return True

    except Exception as e:
        print(f"✗ Alpha Vantage API error: {e}")
        return False


def test_yahoo_finance():
    """Test Yahoo Finance API"""
    print("\n=== Testing Yahoo Finance API ===")

    try:
        api = YahooFinanceAPI()

        print("Fetching AAPL info...")
        info = api.get_info('AAPL')
        print(f"✓ Company: {info['name']}")
        print(f"✓ Market Cap: ${info['market_cap']:,.0f}")

        print("Fetching AAPL historical data...")
        hist = api.get_historical_data('AAPL', period='1mo')
        print(f"✓ Historical data: {len(hist)} days")

        print("✓ Yahoo Finance API working correctly")
        return True

    except Exception as e:
        print(f"✗ Yahoo Finance API error: {e}")
        return False


async def main():
    """Run all API tests"""
    print("Financial Analysis API Connectivity Test")
    print("=" * 50)

    # Test Alpha Vantage
    av_success = await test_alpha_vantage()

    # Test Yahoo Finance
    yf_success = test_yahoo_finance()

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY:")
    print(f"  Alpha Vantage: {'✓ PASS' if av_success else '✗ FAIL'}")
    print(f"  Yahoo Finance: {'✓ PASS' if yf_success else '✗ FAIL'}")

    if av_success and yf_success:
        print("\n✓ All APIs working correctly!")
        return 0
    else:
        print("\n✗ Some APIs failed - check your configuration")
        return 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
