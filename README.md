# 📈 Crypto Backtesting Framework  
**Mean Reversion + Momentum Strategy**

This repository contains a **Python-based backtesting engine** for evaluating a quantitative crypto trading strategy that combines **mean reversion**, **trend filtering**, and **momentum confirmation**.

The goal is **research and hypothesis testing**, not production trading.

---

## 🧠 Strategy Overview

The strategy attempts to buy **temporarily oversold assets** *only* when the **long-term trend is positive**, aiming to avoid catching falling knives.

### Core Philosophy

> Buy quality tokens when they are oversold, **but only in confirmed uptrends**.

This is not pure mean reversion and not pure momentum — it’s a hybrid.

---

## ✅ Entry Criteria

A token becomes eligible on **rebalance days** if **all** of the following are true:

1. **Long-term uptrend**
   - Price > 200-day simple moving average

2. **Oversold condition (relaxed)**
   - RSI < 50 **OR**
   - Price near lower Bollinger Band (`bb_position < 0.4`)

3. **Momentum confirmation**
   - 30-day momentum > -15%  
   (Allows pullbacks but avoids collapsing assets)

4. **Liquidity filter**
   - Volume ratio > 0.5 (above-average volume)

5. **Quality ranking**

   Candidates are ranked using a composite score favoring:
   - Lower volatility
   - Lower RSI
   - Higher volume

The **top N (max 10)** tokens are selected and equally weighted.

---

## ❌ Exit Rules

Positions are exited immediately if **any** of the following conditions are met:

1. **Stop-loss**
   - Total return < **-12%**

2. **Overbought condition**
   - RSI > 70

3. **Profit-taking**
   - Price reaches upper Bollinger Band (`bb_position > 0.95`)

The portfolio is **rebalanced every N days** (default: 7).

---

## 🧪 Backtesting Workflow

The full pipeline is orchestrated by `run_backtest()`:

1. **Data Cleaning**
   - Handled by `clean_data()`
   - Filters invalid prices, missing values, and unusable tokens

2. **Indicator Calculation**
   - Moving averages
   - RSI
   - Bollinger Bands
   - Momentum
   - Volatility
   - Volume ratios

3. **Strategy Simulation**
   - Capital-based portfolio simulation
   - Equal-weight allocation
   - Daily mark-to-market valuation

4. **Performance Metrics**
   - Returns
   - Drawdowns
   - Risk-adjusted metrics (implementation-dependent)

5. **Visualization**
   - Portfolio equity curve saved as an image

---

## 📁 Project Structure

src/
├── backtesting/
│ ├── data_cleaner.py # Data filtering & preprocessing
│ ├── indicators.py # Technical indicators
│ ├── performance.py # Performance metrics
│ ├── plot.py # Result visualization
│ └── main.py # Backtesting orchestration

---

## 🚀 How to Run

### 1. Install dependencies

```
bash
pip install -r requirements.txt
```

### 2. Run the backtest

python src/backtesting/main.py

Or programmatically:

from src.backtesting.main import run_backtest

results = run_backtest(
    initial_capital=10000,
    rebalance_days=7,
    output_filename="backtest_results.png"
)


## 📊 Output

After running the backtest, you will get:

- **Equity curve plot**  
  Saved in the backtesting folder as the filename specified (`backtest_results.png` by default).

- **Portfolio DataFrame**  
  Contains daily portfolio value and number of active positions.

- **Performance metrics**  
  Summary statistics such as returns, drawdowns, and other risk-adjusted measures.

---

## ⚠️ Limitations

This backtesting framework is for research and educational purposes only. Key limitations include:

- ❌ No transaction costs  
- ❌ No slippage  
- ❌ No liquidity constraints  
- ❌ No order book simulation  
- ❌ Daily resolution only  
- ❌ Possible survivorship bias  
- ❌ Indicators use rolling historical windows, which can introduce subtle lookahead bias

> ⚠️ This code is **not yet suitable for live trading**.  
> Transaction costs, execution delays, and liquidity constraints must be added before deploying live.

---

## 🧩 Purpose

- Test quantitative trading hypotheses  
- Compare strategy variants  
- Learn what works or fails without risking capital  

This code is **not a trading system**—it is purely a research tool.  

> To make it live, you need to implement **transaction costs, slippage, live data feeds, and order execution**.


