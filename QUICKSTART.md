# Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies

```bash
cd charlotte

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install package
pip install -e .
```

### 2. Configure API Keys

Edit `config/.env`:

```bash
# Get FREE API key from: https://www.alphavantage.co/support/#api-key
ALPHA_VANTAGE_API_KEY=YOUR_KEY_HERE

# Replace with your email (required by SEC)
SEC_USER_AGENT=FinancialAnalysis your.email@example.com
```

**Getting Alpha Vantage API Key (FREE):**
1. Visit: https://www.alphavantage.co/support/#api-key
2. Enter your email
3. Receive key instantly
4. Copy to `.env` file

### 3. Initialize Cache

```bash
python scripts/setup_cache.py
```

### 4. Test Installation

```bash
# View configuration
fa info

# Test API connectivity (after adding your key)
fa test-api alpha-vantage

# Show examples
fa examples
```

### 5. Generate Your First Report

```bash
# Basic analysis
fa graham-valuation AAPL

# With browser auto-open
fa graham-valuation MSFT -b

# Custom output path
fa graham-valuation GOOGL -o reports/google.html
```

## What You Get

Each report includes:

✅ **Four Graham Valuation Methods**
- Graham Number: `√(22.5 × EPS × BVPS)`
- Net-Net NCAV: Deep value opportunities
- Normalized Earnings: 7-10 year average
- Dividend-Adjusted: Growth-adjusted value

✅ **Margin of Safety Analysis**
- Visual gauge chart
- Individual margins for each method
- Buy/Hold/Avoid signals

✅ **Defensive Investor Checklist**
- 8 criteria from *The Intelligent Investor*
- Pass/fail for each criterion
- Overall score

✅ **Interactive Charts**
- Valuation comparison bar chart
- Price history with Graham Number overlay
- Financial trends (revenue, earnings)
- Defensive checklist visualization

✅ **Professional HTML Report**
- Self-contained (no server needed)
- Print-ready styling
- Mobile-responsive
- Shareable via email/browser

## Common Commands

```bash
# Analyze a stock
fa graham-valuation SYMBOL

# Options:
#   -o PATH    Output file path
#   -b         Open in browser

# Clear cache
fa clear-cache           # Expired only
fa clear-cache --all     # Everything

# Test APIs
fa test-api alpha-vantage
fa test-api yahoo
fa test-api all

# View configuration
fa info

# Show examples
fa examples

# Help
fa --help
fa graham-valuation --help
```

## Example Output

After running `fa graham-valuation AAPL`, you'll see:

```
╭─────────────────────────────────╮
│ Graham Deep Value Analysis      │
│ Symbol: AAPL                    │
╰─────────────────────────────────╯

⠹ Fetching data from APIs...
⠹ Analyzing fundamentals...
✓ Analysis complete!

✓ Report generated successfully!
Location: output/reports/graham_AAPL_20260306_143022.html
```

Open the HTML file in your browser to view the full interactive report!

## Batch Analysis

Analyze multiple stocks:

```bash
# Basic loop
for ticker in AAPL MSFT GOOGL AMZN; do
    fa graham-valuation $ticker
done

# With custom output directory
mkdir -p reports/tech_giants
for ticker in AAPL MSFT GOOGL AMZN; do
    fa graham-valuation $ticker -o "reports/tech_giants/${ticker}.html"
done
```

## Understanding the Results

### Margin of Safety

- **≥ 50%**: STRONG BUY (enterprising investor)
- **30-50%**: BUY (defensive investor)
- **15-30%**: HOLD (enterprising only)
- **0-15%**: AVOID
- **< 0%**: SELL (overvalued)

### Defensive Checklist

Pass at least 6 of 8 criteria:
1. ✓ Current Ratio ≥ 2.0
2. ✓ Debt/Equity < 0.5
3. ✓ 8+ years positive earnings
4. ✓ 20+ years dividends
5. ✓ P/E ≤ 15
6. ✓ P/B ≤ 1.5
7. ✓ P/E × P/B ≤ 22.5
8. ✓ Market cap ≥ $2B

## Troubleshooting

### "Alpha Vantage API key required"
**Solution**: Add your free API key to `config/.env`
Get key: https://www.alphavantage.co/support/#api-key

### "API rate limit exceeded"
**Solution**: Free tier = 5 calls/min, 500/day
- Wait 1 minute between stocks
- Use cache (automatically enabled)
- Run `fa clear-cache` to remove expired entries

### "SEC_USER_AGENT must be set"
**Solution**: Replace `example.com` with your real email in `config/.env`
```
SEC_USER_AGENT=FinancialAnalysis your@email.com
```

### Charts not displaying
**Solution**:
- Check internet connection (Plotly.js from CDN)
- Try different browser
- Disable ad blockers

### "No module named 'financial_analysis'"
**Solution**:
```bash
source venv/bin/activate
pip install -e .
```

## API Limits

**Alpha Vantage (Free Tier):**
- 5 API calls per minute
- 500 API calls per day
- Use cache to minimize calls

**Yahoo Finance:**
- No official limits
- Recommended: < 2000 requests/hour

**Caching:**
- Quotes: 5 minutes
- Fundamentals: 24 hours
- Filings: 7 days

## Next Steps

1. **Analyze your portfolio**: Run reports for all your holdings
2. **Compare stocks**: Generate reports for competing companies
3. **Watch list**: Track value opportunities over time
4. **Share reports**: Email HTML files to others

## Resources

- Full README: `README.md`
- Skills framework: `FINANCIAL_ANALYSIS_SKILLS.md`
- Alpha Vantage docs: https://www.alphavantage.co/documentation/
- Ben Graham's book: *The Intelligent Investor*

## Support

For issues or questions:
- Check `README.md` for detailed documentation
- Run `fa --help` for command reference
- Run `fa examples` for usage examples

---

**Ready to find undervalued stocks? Start analyzing!** 📈
