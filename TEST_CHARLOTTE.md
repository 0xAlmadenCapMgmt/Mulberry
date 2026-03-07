# Testing Charlotte - Quick Guide

## After Adding Your API Key

### 1. Test Configuration
\`\`\`bash
cd charlotte
source venv/bin/activate
fa info
\`\`\`

Expected: Should show your API key (masked) and "✓ Configuration is valid"

### 2. Test API Connectivity
\`\`\`bash
fa test-api alpha-vantage
\`\`\`

Expected output:
\`\`\`
[Charlotte banner]

Testing Alpha Vantage API
✓ Quote: $XXX.XX
✓ Company: Apple Inc.
✓ Alpha Vantage API working correctly
\`\`\`

### 3. Test Yahoo Finance (no key needed)
\`\`\`bash
fa test-api yahoo
\`\`\`

### 4. Test Both APIs
\`\`\`bash
fa test-api all
\`\`\`

## Your First Analysis

### Generate Graham Valuation Report
\`\`\`bash
# Analyze Apple
fa graham-valuation AAPL

# Or auto-open in browser
fa graham-valuation AAPL -b
\`\`\`

Expected output:
\`\`\`
[Charlotte banner displays]

╭─────────────────────────────────╮
│ Charlotte Analysis              │
│ Symbol: AAPL                    │
╰─────────────────────────────────╯

⠹ Fetching data from APIs...
⠹ Analyzing fundamentals...
✓ Analysis complete!

✓ Report generated successfully!
Location: output/reports/graham_AAPL_20260306_HHMMSS.html
\`\`\`

### Open the Report
\`\`\`bash
# The report will be in output/reports/
open output/reports/graham_AAPL_*.html
\`\`\`

## Example Stocks to Analyze

### Tech Giants
\`\`\`bash
fa graham-valuation AAPL  # Apple
fa graham-valuation MSFT  # Microsoft
fa graham-valuation GOOGL # Google
\`\`\`

### Value Stocks (typically)
\`\`\`bash
fa graham-valuation INTC  # Intel
fa graham-valuation BAC   # Bank of America
fa graham-valuation WFC   # Wells Fargo
fa graham-valuation CVX   # Chevron
\`\`\`

### Consumer Staples
\`\`\`bash
fa graham-valuation KO    # Coca-Cola
fa graham-valuation PG    # Procter & Gamble
fa graham-valuation WMT   # Walmart
\`\`\`

## Troubleshooting

### "Alpha Vantage API key required"
→ Add your key to \`config/.env\`

### "API rate limit exceeded"
→ Wait 1 minute (free tier = 5 calls/min)
→ Or use cache (run same stock again - instant!)

### "SEC_USER_AGENT must be set"
→ Replace \`example.com\` with real email in \`.env\`

### Charts not displaying in report
→ Check internet connection (Plotly.js from CDN)

## What to Look For in Reports

### Strong Buy Signal
- ✅ Margin of Safety ≥ 50%
- ✅ Current Price < Graham Number
- ✅ Defensive Checklist: 6+ criteria passed
- ✅ Net-Net opportunity (rare!)

### Buy Signal
- ✅ Margin of Safety 30-50%
- ✅ Price near Graham Number
- ✅ Good financial strength

### Avoid
- ❌ Margin of Safety < 15%
- ❌ Price > Intrinsic Values
- ❌ Poor financial ratios

## Batch Analysis

### Analyze multiple stocks
\`\`\`bash
# Create list
STOCKS=(AAPL MSFT GOOGL AMZN INTC)

# Analyze all (wait 15 sec between to respect rate limit)
for ticker in "\${STOCKS[@]}"; do
    fa graham-valuation $ticker
    sleep 15
done
\`\`\`

### Compare reports
\`\`\`bash
open output/reports/*.html
\`\`\`

## Happy Analyzing! 📈

Charlotte is ready to help you find undervalued stocks!
