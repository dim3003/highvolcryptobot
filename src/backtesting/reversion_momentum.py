import psycopg2
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from src.data.db import DBService
from src.db_config import DB_CONFIG
from src.backtesting.stablecoins import ARBITRUM_STABLECOINS

def clean_data():
    with psycopg2.connect(**DB_CONFIG) as conn:
        db_service = DBService(conn)
        df = db_service.get_prices()
        
        # Remove stablecoins
        stablecoin_addresses = list(ARBITRUM_STABLECOINS.keys())
        df_filtered = df[~df['token_address'].isin(stablecoin_addresses)]
        
        print(f"Tokens before filtering: {df_filtered['token_address'].nunique()}")
        
        # Apply quality filters
        df_cleaned = apply_quality_filters(df_filtered)
        
        print(f"Tokens after filtering: {df_cleaned['token_address'].nunique()}")
        
        return df_cleaned

def apply_quality_filters(df):
    """Remove tokens that don't meet quality criteria"""
    tokens_to_keep = []
    
    for token_addr in df['token_address'].unique():
        token_data = df[df['token_address'] == token_addr].sort_values('timestamp')
        
        # Minimum market cap - want established tokens
        avg_mcap = token_data['market_cap'].mean()
        if avg_mcap < 5_000_000:
            continue
        
        # Require sufficient data
        if len(token_data) < 730:
            continue
        
        # Filter extreme volatility
        price_changes = token_data['value'].pct_change().abs()
        max_change = price_changes.max()
        if max_change > 2.0:
            continue
        
        # Reject tokens with too many zero-volume days
        if (token_data['total_volume'] == 0).sum() > len(token_data) * 0.1:
            continue
        
        tokens_to_keep.append(token_addr)
    
    df_cleaned = df[df['token_address'].isin(tokens_to_keep)]
    print(f"✅ Kept {len(tokens_to_keep)} tokens after filtering")
    return df_cleaned

def calculate_indicators(df):
    """Calculate technical indicators for mean reversion + momentum strategy"""
    df_with_indicators = []
    
    for token_addr in df['token_address'].unique():
        token_data = df[df['token_address'] == token_addr].sort_values('timestamp').copy()
        
        # Calculate returns
        token_data['returns'] = token_data['value'].pct_change()
        
        # Moving averages for trend
        token_data['sma_50'] = token_data['value'].rolling(window=50).mean()
        token_data['sma_200'] = token_data['value'].rolling(window=200).mean()
        
        # Bollinger Bands for mean reversion
        token_data['bb_middle'] = token_data['value'].rolling(window=20).mean()
        token_data['bb_std'] = token_data['value'].rolling(window=20).std()
        token_data['bb_upper'] = token_data['bb_middle'] + (2 * token_data['bb_std'])
        token_data['bb_lower'] = token_data['bb_middle'] - (2 * token_data['bb_std'])
        
        # Distance from BB bands (mean reversion signal)
        token_data['bb_position'] = (token_data['value'] - token_data['bb_lower']) / (token_data['bb_upper'] - token_data['bb_lower'])
        
        # RSI for oversold/overbought
        token_data['rsi'] = calculate_rsi(token_data['value'], 14)
        
        # Momentum indicators
        token_data['momentum_7d'] = token_data['value'].pct_change(7)
        token_data['momentum_30d'] = token_data['value'].pct_change(30)
        
        # Volume trend
        token_data['volume_sma_20'] = token_data['total_volume'].rolling(window=20).mean()
        token_data['volume_ratio'] = token_data['total_volume'] / token_data['volume_sma_20']
        
        # Volatility
        token_data['volatility_30d'] = token_data['returns'].rolling(window=30).std() * np.sqrt(365)
        
        df_with_indicators.append(token_data)
    
    return pd.concat(df_with_indicators, ignore_index=True)

def calculate_rsi(prices, period=14):
    """Calculate Relative Strength Index"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def backtest_strategy(df, initial_capital=10000, rebalance_days=7):
    """
    MEAN REVERSION + MOMENTUM STRATEGY
    
    Philosophy: Buy quality tokens when they're oversold/undervalued, 
    but only if the long-term trend is up.
    
    Selection Criteria:
    1. Price above 200-day MA (long-term uptrend)
    2. RSI < 40 (oversold) OR price near lower Bollinger Band
    3. Positive 30-day momentum (recent strength)
    4. Above-average volume (conviction in moves)
    5. Lower volatility preferred (quality over chaos)
    
    Exit Rules:
    1. RSI > 70 (overbought)
    2. Price hits upper Bollinger Band
    3. Stop loss at -10% (tight risk management)
    4. Weekly rebalancing
    """
    dates = sorted(df['timestamp'].unique())
    portfolio_values = []
    capital = initial_capital
    current_positions = {}
    
    print(f"\n=== MEAN REVERSION + MOMENTUM STRATEGY ===")
    print(f"Initial Capital: ${initial_capital:,.2f}")
    print(f"Strategy: Buy oversold tokens in uptrends")
    print(f"Rebalancing: Every {rebalance_days} days")
    print(f"Backtest Period: {dates[0]} to {dates[-1]}")
    print(f"Total Days: {len(dates)}\n")
    
    last_rebalance = 200  # Start after 200-day MA is available
    
    for i in range(200, len(dates)):
        current_date = dates[i]
        
        # Check if it's rebalancing day
        should_rebalance = (i - last_rebalance) >= rebalance_days
        
        if should_rebalance:
            # Get data up to current date
            historical_data = df[df['timestamp'] <= current_date]
            
            # Get latest metrics for each token
            latest_metrics = historical_data.groupby('token_address').agg({
                'value': 'last',
                'sma_50': 'last',
                'sma_200': 'last',
                'bb_position': 'last',
                'rsi': 'last',
                'momentum_30d': 'last',
                'volume_ratio': 'last',
                'volatility_30d': 'last'
            }).reset_index()
            
            # Remove NaN values
            latest_metrics = latest_metrics.dropna()
            
            if len(latest_metrics) == 0:
                continue
            
            # Apply strategy filters
            candidates = latest_metrics.copy()
            
            # 1. Long-term uptrend: Price above 200-day MA
            candidates = candidates[candidates['value'] > candidates['sma_200']]
            
            # 2. Oversold conditions: RSI < 40 OR near lower BB
            candidates = candidates[
                (candidates['rsi'] < 40) | 
                (candidates['bb_position'] < 0.3)
            ]
            
            # 3. Recent momentum positive (recovering, not falling knife)
            candidates = candidates[candidates['momentum_30d'] > -0.1]  # Allow slight negative
            
            # 4. Above average volume (conviction)
            candidates = candidates[candidates['volume_ratio'] > 0.8]
            
            if len(candidates) == 0:
                # If no candidates, hold cash or keep existing positions
                continue
            
            # 5. Rank by quality score (prefer lower volatility + better RSI)
            candidates['quality_score'] = (
                (40 - candidates['rsi']) / 40 * 0.5 +  # Lower RSI = higher score
                (1 - candidates['volatility_30d'] / candidates['volatility_30d'].max()) * 0.3 +  # Lower vol = higher score
                (candidates['volume_ratio'] / candidates['volume_ratio'].max()) * 0.2  # Higher volume = higher score
            )
            
            # Select top 8 tokens by quality score
            n_tokens = min(8, len(candidates))
            selected_tokens = candidates.nlargest(n_tokens, 'quality_score')
            
            # Update positions
            if len(selected_tokens) > 0:
                current_positions = {}
                allocation_per_token = capital / len(selected_tokens)
                
                for _, token_row in selected_tokens.iterrows():
                    current_positions[token_row['token_address']] = {
                        'entry_price': token_row['value'],
                        'allocation': allocation_per_token
                    }
            
            last_rebalance = i
        
        # Calculate daily returns with exit rules
        if i < len(dates) - 1 and len(current_positions) > 0:
            next_date = dates[i + 1]
            daily_portfolio_return = 0
            tokens_to_exit = []
            
            for token_addr, position in list(current_positions.items()):
                current_price_data = df[(df['token_address'] == token_addr) & 
                                       (df['timestamp'] == current_date)]
                next_price_data = df[(df['token_address'] == token_addr) & 
                                    (df['timestamp'] == next_date)]
                
                if len(current_price_data) > 0 and len(next_price_data) > 0:
                    current_price = current_price_data['value'].values[0]
                    next_price = next_price_data['value'].values[0]
                    current_rsi = current_price_data['rsi'].values[0]
                    current_bb_pos = current_price_data['bb_position'].values[0]
                    
                    # Calculate daily return
                    daily_return = (next_price - current_price) / current_price
                    
                    # Check exit conditions
                    entry_price = position['entry_price']
                    total_return = (next_price - entry_price) / entry_price
                    
                    # Exit rule 1: Stop loss at -10%
                    if total_return < -0.10:
                        tokens_to_exit.append(token_addr)
                        daily_portfolio_return += total_return / len(current_positions)
                    
                    # Exit rule 2: Overbought (RSI > 70)
                    elif current_rsi > 70:
                        tokens_to_exit.append(token_addr)
                        daily_portfolio_return += total_return / len(current_positions)
                    
                    # Exit rule 3: Hit upper Bollinger Band (take profit)
                    elif current_bb_pos > 0.95:
                        tokens_to_exit.append(token_addr)
                        daily_portfolio_return += total_return / len(current_positions)
                    
                    else:
                        # Hold position
                        daily_portfolio_return += daily_return / len(current_positions)
            
            # Remove exited positions
            for token in tokens_to_exit:
                if token in current_positions:
                    del current_positions[token]
            
            # Update capital
            capital = capital * (1 + daily_portfolio_return)
        
        portfolio_values.append({
            'date': current_date,
            'portfolio_value': capital,
            'n_tokens': len(current_positions),
        })
    
    portfolio_df = pd.DataFrame(portfolio_values)
    return portfolio_df

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

def plot_backtest_results(portfolio_df):
    """Plot backtest results"""
    fig, axes = plt.subplots(3, 1, figsize=(14, 12))
    
    # Plot 1: Portfolio Value Over Time
    ax1 = axes[0]
    ax1.plot(portfolio_df['date'], portfolio_df['portfolio_value'], linewidth=2, label='Strategy', color='green')
    ax1.set_title('Mean Reversion + Momentum Strategy - Portfolio Value', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Portfolio Value ($)', fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=10000, color='gray', linestyle='--', alpha=0.5, label='Initial Capital')
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
    portfolio_df['cumulative_return'] = (1 + portfolio_df['daily_return']).cumprod()
    portfolio_df['running_max'] = portfolio_df['cumulative_return'].expanding().max()
    portfolio_df['drawdown'] = (portfolio_df['cumulative_return'] - portfolio_df['running_max']) / portfolio_df['running_max']
    
    ax3.fill_between(portfolio_df['date'], portfolio_df['drawdown'] * 100, 0, alpha=0.3, color='red')
    ax3.plot(portfolio_df['date'], portfolio_df['drawdown'] * 100, color='red', linewidth=1)
    ax3.set_title('Drawdown Over Time', fontsize=14, fontweight='bold')
    ax3.set_xlabel('Date', fontsize=12)
    ax3.set_ylabel('Drawdown (%)', fontsize=12)
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('mean_reversion_backtest.png', dpi=300, bbox_inches='tight')
    print("\n📊 Charts saved as 'mean_reversion_backtest.png'")
    plt.show()

if __name__ == '__main__':
    # Step 1: Clean data
    df_cleaned = clean_data()
    
    # Step 2: Calculate indicators
    print("\n📊 Calculating technical indicators...")
    df_with_indicators = calculate_indicators(df_cleaned)
    
    # Step 3: Backtest strategy
    portfolio_df = backtest_strategy(
        df_with_indicators, 
        initial_capital=10000,
        rebalance_days=7
    )
    
    # Step 4: Calculate performance metrics
    metrics = calculate_performance_metrics(portfolio_df, initial_capital=10000)
    
    # Step 5: Visualize results
    plot_backtest_results(portfolio_df)
