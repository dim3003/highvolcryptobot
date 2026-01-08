import psycopg2
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from src.data.db import DBService
from src.db_config import DB_CONFIG
from src.backtesting.stablecoins import ARBITRUM_STABLECOINS

def calculate_performance_metrics(portfolio_df, initial_capital=10000):
    """Calculate strategy performance metrics"""
    final_value = portfolio_df['portfolio_value'].iloc[-1]
    total_return = (final_value - initial_capital) / initial_capital
    
    portfolio_df['daily_return'] = portfolio_df['portfolio_value'].pct_change()
    
    n_days = len(portfolio_df)
    years = n_days / 365
    
    annualized_return = (final_value / initial_capital) ** (1 / years) - 1
    volatility = portfolio_df['daily_return'].std() * np.sqrt(365)
    sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
    
    cumulative = (1 + portfolio_df['daily_return']).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()
    
    win_rate = (portfolio_df['daily_return'] > 0).sum() / len(portfolio_df['daily_return'].dropna())
    calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
    
    print("\n" + "="*60)
    print("MEAN REVERSION + MOMENTUM STRATEGY")
    print("="*60)
    print(f"Initial Capital:        ${initial_capital:,.2f}")
    print(f"Final Portfolio Value:  ${final_value:,.2f}")
    print(f"Total Return:           {total_return*100:.2f}%")
    print(f"Annualized Return:      {annualized_return*100:.2f}%")
    print(f"Annualized Volatility:  {volatility*100:.2f}%")
    print(f"Sharpe Ratio:           {sharpe_ratio:.2f}")
    print(f"Calmar Ratio:           {calmar_ratio:.2f}")
    print(f"Maximum Drawdown:       {max_drawdown*100:.2f}%")
    print(f"Win Rate:               {win_rate*100:.2f}%")
    print(f"Backtest Days:          {n_days}")
    print(f"Avg Tokens Held:        {portfolio_df['n_tokens'].mean():.1f}")
    print("="*60)
    print("\nBitcoin benchmark ~70% annualized over similar period")
    print("="*60)
    
    return {
        'final_value': final_value,
        'total_return': total_return,
        'annualized_return': annualized_return,
        'volatility': volatility,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'calmar_ratio': calmar_ratio
    }
