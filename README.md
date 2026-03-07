# Charlotte - Financial Analysis Report Generator

```
 ██████╗██╗  ██╗ █████╗ ██████╗ ██╗      ██████╗ ████████╗████████╗███████╗
██╔════╝██║  ██║██╔══██╗██╔══██╗██║     ██╔═══██╗╚══██╔══╝╚══██╔══╝██╔════╝
██║     ███████║███████║██████╔╝██║     ██║   ██║   ██║      ██║   █████╗
██║     ██╔══██║██╔══██║██╔══██╗██║     ██║   ██║   ██║      ██║   ██╔══╝
╚██████╗██║  ██║██║  ██║██║  ██║███████╗╚██████╔╝   ██║      ██║   ███████╗
 ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝ ╚═════╝    ╚═╝      ╚═╝   ╚══════╝
```

**Charlotte** is a professional stock analysis platform implementing **Ben Graham's value investing principles** from *The Intelligent Investor*. Charlotte generates comprehensive HTML reports with interactive visualizations, four Graham valuation methods, and defensive/enterprising investor checklists.

## Features

- **Four Graham Valuation Methods**
  - Graham Number Formula: `√(22.5 × EPS × BVPS)`
  - Net-Net Working Capital (NCAV): Deep value opportunities
  - Normalized Earnings: 7-10 year average earnings valuation
  - Dividend-Adjusted: Growth and interest rate adjusted value

- **Comprehensive Analysis**
  - Margin of safety calculation (target: 30%+ for defensive, 50%+ for enterprising)
  - 8-point defensive investor checklist
  - Enterprising investor opportunity assessment
  - Financial strength and profitability metrics
  - Historical earnings trends

- **Professional Reports**
  - Interactive Plotly charts (zoom, pan, hover)
  - Self-contained HTML files (no server required)
  - Print-ready styling
  - Mobile-responsive design

- **Performance**
  - Async API calls (5-10x faster than synchronous)
  - SQLite caching with TTL (reduces API costs by 90%+)
  - Parallel data fetching from multiple sources

## Installation

### 1. Clone or download the repository

```bash
cd charlotte
```

### 2. Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -e .
```

### 4. Configure API keys

```bash
cp config/.env.example config/.env
```

Edit `config/.env` and add your API keys:

```bash
# Get free API key from https://www.alphavantage.co/support/#api-key
ALPHA_VANTAGE_API_KEY=your_key_here

# Optional: Financial Modeling Prep (for additional data)
FMP_API_KEY=your_key_here

# Required by SEC (replace with your real email)
SEC_USER_AGENT=YourCompany your.email@example.com
```

### 5. Initialize cache database

```bash
python scripts/setup_cache.py
```

### 6. Test API connectivity

```bash
python scripts/test_apis.py
```

## Usage

### Basic Graham Valuation Analysis

```bash
fa graham-valuation AAPL
```

Generates comprehensive Graham valuation report for Apple Inc.

### Custom Output Path

```bash
fa graham-valuation MSFT -o reports/microsoft_analysis.html
```

### Auto-Open in Browser

```bash
fa graham-valuation GOOGL -b
```

Generates report and opens in your default browser.

### Batch Analysis

```bash
# Analyze multiple stocks
for ticker in AAPL MSFT GOOGL INTC; do
    fa graham-valuation $ticker
done
```

### Cache Management

```bash
# Clear expired cache entries
fa clear-cache

# Clear entire cache
fa clear-cache --all
```

### View Configuration

```bash
fa info
```

### Test APIs

```bash
fa test-api alpha-vantage
fa test-api all
```

### Show Examples

```bash
fa examples
```

## Command Reference

```bash
fa graham-valuation SYMBOL [OPTIONS]
  Generate Graham valuation report

  Options:
    -o, --output PATH      Output file path (default: auto-generated)
    -b, --open-browser     Open report in browser after generation

fa clear-cache [OPTIONS]
  Clear expired cache entries

  Options:
    -a, --all              Clear all cache (including valid entries)

fa info
  Display configuration and system information

fa test-api {alpha-vantage|yahoo|all}
  Test API connectivity

fa examples
  Show usage examples

fa --version
  Show version

fa --help
  Show help message
```

## Report Sections

Generated reports include:

1. **Executive Summary**
   - Current price vs intrinsic value
   - Average margin of safety
   - Investment recommendation

2. **Graham's Four Valuations**
   - Interactive bar chart comparing methods
   - Individual margin of safety for each method
   - Buy/hold/avoid signals

3. **Margin of Safety Gauge**
   - Visual gauge showing safety margin
   - Color-coded zones (green: >50%, yellow: 15-30%, red: <0%)

4. **Defensive Investor Checklist**
   - 8 criteria from *The Intelligent Investor*
   - Pass/fail for each criterion
   - Overall score

5. **Enterprising Investor Assessment**
   - Net-net opportunities
   - Low P/E with growth
   - Financial strength + undervaluation
   - Contrarian plays

6. **Price History**
   - Historical price chart with Graham Number overlay
   - Identifies buy zones

7. **Financial Trends**
   - Revenue and earnings over time
   - Growth rates and stability

8. **Key Metrics**
   - EPS, Book Value, P/E, P/B
   - Current Ratio, Debt/Equity
   - ROE, Dividend Yield

## Technology Stack

- **CLI**: Click + Rich (progress bars, styling)
- **Async**: asyncio + aiohttp (parallel API calls)
- **Data**: pandas + numpy
- **Visualization**: Plotly (interactive HTML charts)
- **Templates**: Jinja2 (HTML report generation)
- **Cache**: SQLite with TTL (via SQLAlchemy)
- **APIs**: Alpha Vantage, Yahoo Finance (yfinance), SEC EDGAR

## Project Structure

```
financial-analysis-app/
├── financial_analysis/          # Main package
│   ├── api/                     # API wrappers
│   │   ├── alpha_vantage.py    # Alpha Vantage async client
│   │   └── yahoo_finance.py    # Yahoo Finance wrapper
│   ├── core/                    # Analysis engines
│   │   ├── graham.py           # Graham valuation methods
│   │   └── stock_analysis.py   # Stock analyzer
│   ├── cache/                   # Caching layer
│   │   ├── database.py         # Cache manager
│   │   └── models.py           # SQLite schemas
│   ├── visualization/           # Chart generation
│   │   └── charts.py           # Plotly charts
│   ├── reports/                 # Report generation
│   │   └── generator.py        # HTML report engine
│   ├── templates/               # Jinja2 templates
│   │   ├── base.html
│   │   └── graham_analysis.html
│   ├── utils/                   # Utilities
│   └── cli.py                   # CLI interface
├── output/
│   └── reports/                 # Generated reports
├── config/
│   └── .env                     # API keys (git-ignored)
├── scripts/
│   ├── setup_cache.py          # Initialize database
│   └── test_apis.py            # Test connectivity
├── requirements.txt
├── setup.py
└── README.md
```

## Data Sources

- **Alpha Vantage**: Company fundamentals, financial statements, time series
- **Yahoo Finance**: Historical prices, dividends, company info
- **SEC EDGAR**: (Future) 10-K/10-Q filings, XBRL data
- **FRED**: (Future) Economic indicators, AAA bond yields

## Graham Methodology

### Graham Number Formula

```
Graham Number = √(22.5 × EPS × Book Value per Share)

Where 22.5 = 15 (max P/E) × 1.5 (max P/B)
```

**Interpretation:**
- Buy when: Stock Price < Graham Number
- Sell when: Stock Price > Graham Number × 1.2

### Net-Net Working Capital (NCAV)

```
NCAV per share = (Current Assets - Total Liabilities) / Shares Outstanding

Buy when: Stock Price < (2/3 × NCAV per share)
```

This provides extreme margin of safety - Graham's favorite method for deep value.

### Normalized Earnings Valuation

```
Intrinsic Value = Average Earnings (7-10 years) × Appropriate P/E

Appropriate P/E:
  - Stable company: 8.5 + (2 × expected growth rate)
  - Conservative: 10-12
  - Maximum for defensive investor: 15
```

### Dividend-Adjusted Formula

```
Value = (EPS × (8.5 + 2g) × 4.4) / Y

Where:
  g = Expected annual earnings growth (%)
  Y = Current yield on AAA corporate bonds (%)
  4.4 = Historical average AAA bond yield
```

### Margin of Safety

```
Margin of Safety = (Intrinsic Value - Market Price) / Intrinsic Value

Target:
  - Defensive Investor: ≥ 30%
  - Enterprising Investor: ≥ 50%
```

## Defensive Investor Checklist

8 criteria from *The Intelligent Investor*:

1. **Adequate Size**: Market cap ≥ $2 billion
2. **Strong Financial Position**: Current ratio ≥ 2.0
3. **Conservative Capital Structure**: Debt/Equity < 0.5
4. **Earnings Stability**: No losses in past 10 years
5. **Dividend Record**: Continuous dividends for 20+ years
6. **Reasonable P/E**: P/E ratio ≤ 15
7. **Modest P/B**: Price/Book ≤ 1.5
8. **Combined Test**: P/E × P/B ≤ 22.5

## Performance Optimization

- **Async API Calls**: Fetch data from multiple sources in parallel
- **SQLite Caching**: Default TTLs:
  - Quotes: 5 minutes (300s)
  - Fundamentals: 24 hours (86400s)
  - SEC Filings: 7 days (604800s)
- **Rate Limiting**: Respects API limits automatically
- **Lazy Loading**: Only fetch data that's needed

## Troubleshooting

### "Alpha Vantage API key required"
- Edit `config/.env` and add your free API key
- Get key from: https://www.alphavantage.co/support/#api-key

### "API rate limit exceeded"
- Alpha Vantage free tier: 5 calls/minute, 500 calls/day
- Use cache to reduce API calls
- Run `fa clear-cache` to clear expired cache

### "No module named 'financial_analysis'"
- Make sure you ran: `pip install -e .`
- Activate virtual environment: `source venv/bin/activate`

### Charts not displaying
- Ensure internet connection (Plotly.js loaded from CDN)
- Try different browser
- Check browser console for JavaScript errors

## Limitations

- **Alpha Vantage Free Tier**: 5 API calls/minute, 500/day
- **Historical Data**: Limited by API availability
- **Real-Time Data**: 15-minute delay (depends on API)
- **International Stocks**: US stocks only (Alpha Vantage limitation)

## Future Enhancements

- [ ] SEC EDGAR filing parser
- [ ] Financial Modeling Prep integration
- [ ] FRED economic indicators
- [ ] Portfolio analysis report
- [ ] PDF export
- [ ] Web UI (FastAPI + React)
- [ ] Email report scheduling
- [ ] Watchlist alerts
- [ ] International stock support

## License

MIT License - see LICENSE file

## Disclaimer

This tool is for educational and informational purposes only. It does not constitute financial, investment, or trading advice. Always conduct your own due diligence and consult with a qualified financial advisor before making investment decisions. Past performance does not guarantee future results.

## References

- Graham, Benjamin. *The Intelligent Investor*. Harper Business, 1949.
- Graham, Benjamin & Dodd, David. *Security Analysis*. McGraw-Hill, 1934.
- Alpha Vantage API: https://www.alphavantage.co/documentation/
- Yahoo Finance (yfinance): https://github.com/ranaroussi/yfinance

## Support

For issues, feature requests, or questions:
- GitHub Issues: [your-repo-url]/issues
- Email: your.email@example.com

---

**Built with ❤️ using Ben Graham's timeless value investing principles**
