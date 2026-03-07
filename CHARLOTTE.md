# 📊 Charlotte - Ben Graham Value Investing Analysis

```
 ██████╗██╗  ██╗ █████╗ ██████╗ ██╗      ██████╗ ████████╗████████╗███████╗
██╔════╝██║  ██║██╔══██╗██╔══██╗██║     ██╔═══██╗╚══██╔══╝╚══██╔══╝██╔════╝
██║     ███████║███████║██████╔╝██║     ██║   ██║   ██║      ██║   █████╗
██║     ██╔══██║██╔══██║██╔══██╗██║     ██║   ██║   ██║      ██║   ██╔══╝
╚██████╗██║  ██║██║  ██║██║  ██║███████╗╚██████╔╝   ██║      ██║   ███████╗
 ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝ ╚═════╝    ╚═╝      ╚═╝   ╚══════╝
```

**Ben Graham Value Investing Analysis**
*Professional Reports • Interactive Charts • Deep Value Discovery*

---

## What is Charlotte?

**Charlotte** is a professional financial analysis platform implementing Benjamin Graham's timeless value investing principles from *The Intelligent Investor*. Named to represent intelligent, systematic, and principled analysis, Charlotte helps investors:

✅ **Find Undervalued Stocks** using four Graham valuation methods
✅ **Calculate Margin of Safety** automatically
✅ **Apply Defensive Investor Criteria** (8-point checklist)
✅ **Generate Professional Reports** with interactive visualizations
✅ **Make Data-Driven Decisions** based on fundamentals, not hype

---

## Why "Charlotte"?

The name **Charlotte** embodies:

- **🧠 Intelligence**: Smart, systematic analysis based on proven principles
- **📊 Precision**: Accurate calculations using Ben Graham's exact formulas
- **💎 Value**: Focus on intrinsic value, not market sentiment
- **📈 Growth**: Long-term wealth building through value investing
- **🎯 Reliability**: Consistent, repeatable methodology

Charlotte represents a trusted analytical companion for value investors.

---

## Quick Start

### Installation

```bash
cd charlotte
source venv/bin/activate
```

### Usage

```bash
# Analyze a stock
fa graham-valuation AAPL

# View configuration
fa info

# Show examples
fa examples

# Test APIs
fa test-api all
```

**When you run any command, you'll see Charlotte's banner greeting you!**

---

## Features

### 🎯 Four Graham Valuation Methods

1. **Graham Number**: `√(22.5 × EPS × BVPS)`
2. **Net-Net NCAV**: Deep value liquidation basis
3. **Normalized Earnings**: 7-10 year average
4. **Dividend-Adjusted**: Growth and interest rate adjusted

### 📊 Comprehensive Analysis

- Margin of Safety calculation
- Defensive Investor 8-point checklist
- Enterprising Investor assessment
- Financial strength metrics
- Historical trends

### 📈 Professional Reports

- Interactive Plotly charts
- Beautiful HTML design
- Mobile-responsive
- Self-contained (no server needed)
- Print-ready

### ⚡ Fast & Efficient

- Async API calls (5-10x faster)
- Smart caching (90% API savings)
- Rate limiting built-in
- Parallel data fetching

---

## Charlotte's Principles

Based on Benjamin Graham's teachings:

### 1. **Margin of Safety**
*"The secret of sound investment is a margin of safety."*
- Buy only when price is significantly below intrinsic value
- Target: 30%+ for defensive, 50%+ for enterprising

### 2. **Mr. Market Allegory**
*"Be fearful when others are greedy, greedy when others are fearful."*
- Exploit market irrationality
- Buy when Mr. Market is pessimistic

### 3. **Investment vs. Speculation**
*"An investment operation promises safety of principal and adequate return."*
- Focus on fundamentals, not price movements
- Thorough analysis before every decision

### 4. **The Defensive Investor**
*"The defensive investor must confine himself to high-grade bonds and leading common stocks."*
- 8-point checklist
- Quality companies at reasonable prices

---

## Sample Charlotte Output

```bash
$ fa graham-valuation AAPL

 ██████╗██╗  ██╗ █████╗ ██████╗ ██╗      ██████╗ ████████╗████████╗███████╗
██╔════╝██║  ██║██╔══██╗██╔══██╗██║     ██╔═══██╗╚══██╔══╝╚══██╔══╝██╔════╝
██║     ███████║███████║██████╔╝██║     ██║   ██║   ██║      ██║   █████╗
██║     ██╔══██║██╔══██║██╔══██╗██║     ██║   ██║   ██║      ██║   ██╔══╝
╚██████╗██║  ██║██║  ██║██║  ██║███████╗╚██████╔╝   ██║      ██║   ███████╗
 ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝ ╚═════╝    ╚═╝      ╚═╝   ╚══════╝

                      Ben Graham Value Investing Analysis
        Professional Reports • Interactive Charts • Deep Value Discovery

╭─────────────────────────────────╮
│ Charlotte Analysis              │
│ Symbol: AAPL                    │
╰─────────────────────────────────╯

⠹ Fetching data from APIs...
⠹ Analyzing fundamentals...
✓ Analysis complete!

✓ Report generated successfully!
Location: output/reports/graham_AAPL_20260306_154523.html
```

---

## Charlotte Workflow

```
1. INPUT
   └─ Stock symbol (e.g., AAPL)

2. DATA COLLECTION (Charlotte gathers)
   ├─ Company fundamentals
   ├─ Financial statements (3 years)
   ├─ Historical prices
   └─ Market data

3. ANALYSIS (Charlotte calculates)
   ├─ Graham Number
   ├─ Net-Net NCAV
   ├─ Normalized Earnings
   ├─ Dividend-Adjusted Value
   ├─ Margin of Safety
   └─ Defensive Checklist

4. VISUALIZATION (Charlotte creates)
   ├─ Valuation comparison chart
   ├─ Margin of safety gauge
   ├─ Price history chart
   ├─ Financial trends
   └─ Checklist visualization

5. OUTPUT
   └─ Professional HTML report
      ├─ Investment recommendation
      ├─ Interactive charts
      ├─ Detailed analysis
      └─ Key metrics
```

---

## Charlotte Commands

| Command | Description | Example |
|---------|-------------|---------|
| `fa graham-valuation SYMBOL` | Analyze stock | `fa graham-valuation AAPL` |
| `fa graham-valuation SYMBOL -b` | Analyze + open browser | `fa graham-valuation MSFT -b` |
| `fa graham-valuation SYMBOL -o PATH` | Custom output | `fa graham-valuation GOOGL -o reports/google.html` |
| `fa info` | Show configuration | `fa info` |
| `fa test-api all` | Test API connectivity | `fa test-api all` |
| `fa clear-cache` | Clear expired cache | `fa clear-cache` |
| `fa examples` | Show usage examples | `fa examples` |
| `fa --version` | Show Charlotte version | `fa --version` |

---

## Charlotte Report Sections

Every Charlotte report includes:

### 1. Executive Summary
- Current price vs intrinsic values
- Average margin of safety
- Investment recommendation

### 2. Valuation Methods
- Interactive bar chart
- Four Graham methods
- Buy/Hold/Avoid signals

### 3. Margin of Safety Gauge
- Visual gauge (0-100%)
- Color zones
- Target threshold

### 4. Defensive Checklist
- 8 criteria with pass/fail
- Visual checklist chart
- Overall score

### 5. Price History
- Historical chart
- Graham Number overlay
- Buy zones highlighted

### 6. Financial Trends
- Revenue over time
- Earnings trends
- Growth analysis

### 7. Key Metrics
- P/E, P/B, Debt/Equity
- Current Ratio, ROE
- Market Cap, Dividend Yield

---

## Getting Help

```bash
fa --help                    # General help
fa graham-valuation --help   # Command help
fa examples                  # Usage examples
fa info                      # Configuration
```

**Documentation:**
- `README.md` - Complete manual
- `QUICKSTART.md` - 5-minute setup
- `NEXT_STEPS.md` - Action items
- `CHARLOTTE.md` - This file

---

## About the Name

**Charlotte** represents:
- **Intelligence**: Smart, data-driven analysis
- **Reliability**: Consistent methodology
- **Value**: Focus on intrinsic worth
- **Precision**: Accurate calculations
- **Trust**: Your analytical companion

Charlotte embodies the spirit of Benjamin Graham's teachings: disciplined, principled, and focused on long-term value creation.

---

## Charlotte's Philosophy

> *"In the short run, the market is a voting machine but in the long run, it is a weighing machine."*
> — Benjamin Graham

Charlotte helps you be a **weigher**, not a **voter**.

### Weighers (Value Investors):
✅ Focus on fundamentals
✅ Calculate intrinsic value
✅ Demand margin of safety
✅ Think long-term
✅ Buy fear, sell greed

### Voters (Speculators):
❌ Follow trends
❌ Trade on sentiment
❌ Chase momentum
❌ Think short-term
❌ Buy high, sell low

**Choose wisely. Be a Charlotte user. Be a weigher.**

---

## Technical Details

- **Version**: 0.1.0
- **CLI Command**: `fa`
- **Language**: Python 3.9+
- **Architecture**: Async, cached, modular
- **APIs**: Alpha Vantage, Yahoo Finance
- **Charts**: Plotly (interactive HTML)
- **Reports**: Jinja2 templates

---

## Next Steps

1. **Setup**: Add Alpha Vantage API key to `config/.env`
2. **Test**: Run `fa test-api all`
3. **Analyze**: Run `fa graham-valuation AAPL`
4. **Learn**: Read the generated HTML report
5. **Discover**: Find undervalued stocks!

---

**Welcome to Charlotte. Let's find value together.** 📈💎

*Built with ❤️ using Ben Graham's timeless principles*
