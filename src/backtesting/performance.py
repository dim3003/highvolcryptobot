import os
import json
import psycopg2
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from src.data.db import DBService
from src.db_config import DB_CONFIG
from src.backtesting.stablecoins import ARBITRUM_STABLECOINS

def calculate_performance_metrics(portfolio_df, initial_capital=10000, filename=None):
    """Calculate strategy performance metrics and optionally save to a file"""

    final_value = portfolio_df['portfolio_value'].iloc[-1]
    total_return = (final_value - initial_capital) / initial_capital

    portfolio_df['daily_return'] = portfolio_df['portfolio_value'].pct_change()

    n_days = len(portfolio_df)
    years = n_days / 365 if n_days > 0 else 0

    annualized_return = (final_value / initial_capital) ** (1 / years) - 1 if years > 0 else 0
    volatility = portfolio_df['daily_return'].std() * np.sqrt(365)
    sharpe_ratio = annualized_return / volatility if volatility > 0 else 0

    cumulative = (1 + portfolio_df['daily_return']).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()

    win_rate = (portfolio_df['daily_return'] > 0).sum() / portfolio_df['daily_return'].dropna().shape[0]
    calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0

    # -----------------------------
    # Final formatted metrics
    # -----------------------------
    metrics = {
        # Dollar values (rounded to dollars)
        "initial_capital_usd": int(round(initial_capital)),
        "final_value_usd": int(round(final_value)),

        # Percentages
        "total_return_pct": round(total_return * 100, 2),
        "annualized_return_pct": round(annualized_return * 100, 2),
        "volatility_pct": round(volatility * 100, 2),
        "max_drawdown_pct": round(max_drawdown * 100, 2),
        "win_rate_pct": round(win_rate * 100, 2),

        # Ratios
        "sharpe_ratio": round(sharpe_ratio, 2),
        "calmar_ratio": round(calmar_ratio, 2),

        # Other
        "backtest_days": int(n_days),
        "avg_tokens_held": round(portfolio_df["n_tokens"].mean(), 2),
    }

    # -----------------------------
    # Pretty print
    # -----------------------------
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Initial Capital        : ${metrics['initial_capital_usd']:,}")
    print(f"Final Portfolio Value  : ${metrics['final_value_usd']:,}")
    print(f"Total Return           : {metrics['total_return_pct']}%")
    print(f"Annualized Return      : {metrics['annualized_return_pct']}%")
    print(f"Annualized Volatility  : {metrics['volatility_pct']}%")
    print(f"Sharpe Ratio           : {metrics['sharpe_ratio']}")
    print(f"Calmar Ratio           : {metrics['calmar_ratio']}")
    print(f"Maximum Drawdown       : {metrics['max_drawdown_pct']}%")
    print(f"Win Rate               : {metrics['win_rate_pct']}%")
    print(f"Backtest Days          : {metrics['backtest_days']}")
    print(f"Avg Tokens Held        : {metrics['avg_tokens_held']}")
    print("=" * 60)
    print("\nBitcoin benchmark ~70% annualized over similar period")
    print("=" * 60)

    # -----------------------------
    # Save metrics
    # -----------------------------
    if filename:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            json.dump(metrics, f, indent=4)
        print(f"\nMetrics saved to {filename}")

    return metrics

