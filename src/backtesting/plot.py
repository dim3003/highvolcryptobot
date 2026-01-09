import matplotlib.pyplot as plt
import pandas as pd
from pandas import DataFrame

def plot_backtest_results(portfolio_df: DataFrame, output_path: str = "backtest_results.png"):
    """Plot backtest results"""
    # Calculate daily_return if not present
    if 'daily_return' not in portfolio_df.columns:
        portfolio_df['daily_return'] = portfolio_df['portfolio_value'].pct_change()
    
    fig, axes = plt.subplots(3, 1, figsize=(14, 12))
    
    # Plot 1: Portfolio Value Over Time
    ax1 = axes[0]
    initial_capital = portfolio_df['portfolio_value'].iloc[0] if len(portfolio_df) > 0 else 10000
    ax1.plot(portfolio_df['date'], portfolio_df['portfolio_value'], linewidth=2, label='Strategy', color='green')
    ax1.set_title('Portfolio Value', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Portfolio Value ($)', fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=initial_capital, color='gray', linestyle='--', alpha=0.5, label='Initial Capital')
    ax1.legend()
    ax1.set_yscale('log')
    
    # Plot 2: Daily Returns Distribution
    ax2 = axes[1]
    returns_pct = portfolio_df['daily_return'].dropna() * 100
    ax2.hist(returns_pct, bins=50, edgecolor='black', alpha=0.7, color='green')
    ax2.set_title('Daily Returns Distribution', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Daily Return (%)', fontsize=12)
    ax2.set_ylabel('Frequency', fontsize=12)
    ax2.axvline(x=0, color='red', linestyle='--', alpha=0.5)
    ax2.axvline(x=returns_pct.mean(), color='darkgreen', linestyle='--', alpha=0.7, label=f'Mean: {returns_pct.mean():.2f}%')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Drawdown Over Time
    ax3 = axes[2]
    portfolio_df = portfolio_df.copy()
    portfolio_df['running_max'] = portfolio_df['portfolio_value'].cummax()
    portfolio_df['drawdown'] = (portfolio_df['portfolio_value'] - portfolio_df['running_max']) / portfolio_df['running_max']

    
    ax3.fill_between(portfolio_df['date'], portfolio_df['drawdown'] * 100, 0, alpha=0.3, color='red')
    ax3.plot(portfolio_df['date'], portfolio_df['drawdown'] * 100, color='red', linewidth=1)
    ax3.set_title('Drawdown Over Time', fontsize=14, fontweight='bold')
    ax3.set_xlabel('Date', fontsize=12)
    ax3.set_ylabel('Drawdown (%)', fontsize=12)
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n📊 Charts saved as '{output_path}'")
    plt.close()
