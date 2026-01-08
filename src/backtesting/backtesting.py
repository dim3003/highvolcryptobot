#!/usr/bin/env python3
"""
Main backtesting script.

Orchestrates the complete backtesting workflow:
1. Data cleaning and filtering
2. Technical indicator calculation
3. Strategy backtesting
4. Performance metrics calculation
5. Results visualization
"""
import os
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from src.backtesting.data_cleaner import clean_data
from src.backtesting.indicators import calculate_indicators
from src.backtesting.performance import calculate_performance_metrics
from src.backtesting.plot import plot_backtest_results
from src.backtesting.slippage import slippage_cost 
from src.backtesting.transaction_costs import apply_transaction_costs 


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
            
            # 2. Oversold conditions: RSI < 50 OR near lower BB (RELAXED)
            candidates = candidates[
                (candidates['rsi'] < 50) | 
                (candidates['bb_position'] < 0.4)
            ]
            
            # 3. Recent momentum positive (recovering, not falling knife)
            candidates = candidates[candidates['momentum_30d'] > -0.15]  # Allow more downside
            
            # 4. Above average volume (conviction)
            candidates = candidates[candidates['volume_ratio'] > 0.5]  # RELAXED from 0.8
            
            if len(candidates) == 0:
                # If no candidates, hold cash or keep existing positions
                continue
            
            # 5. Rank by quality score (prefer lower volatility + better RSI)
            candidates['quality_score'] = (
                (40 - candidates['rsi']) / 40 * 0.5 +  # Lower RSI = higher score
                (1 - candidates['volatility_30d'] / candidates['volatility_30d'].max()) * 0.3 +  # Lower vol = higher score
                (candidates['volume_ratio'] / candidates['volume_ratio'].max()) * 0.2  # Higher volume = higher score
            )
            
            # Select top 10 tokens by quality score (INCREASED)
            n_tokens = min(10, len(candidates))
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
                    
                    # ---------- 1. Calculate raw daily return ----------
                    daily_return = (next_price - current_price) / current_price

                    # ---------- 2. Apply slippage ----------
                    # Example: assume pool liquidity = 100,000 USD for simplicity
                    pool_liquidity = 5_000_000
                    slippage_fraction = slippage_cost(position['allocation'], pool_liquidity)
                    daily_return -= slippage_fraction  # reduce return due to slippage

                    # ---------- 3. Apply transaction costs ----------
                    tx_cost_fraction = apply_transaction_costs(position['allocation']) / position['allocation']
                    daily_return -= tx_cost_fraction  # reduce return due to fees + gas

                    # ---------- 4. Check exit conditions ----------
                    entry_price = position['entry_price']
                    total_return = (next_price - entry_price) / entry_price

                    if total_return < -0.12 or current_rsi > 70 or current_bb_pos > 0.95:
                        tokens_to_exit.append(token_addr)
                        daily_portfolio_return += daily_return / len(current_positions)
                    else:
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# Get the backtesting folder path for saving plots
BACKTESTING_DIR = Path(__file__).parent


def run_backtest(
    initial_capital: float = 10000,
    rebalance_days: int = 7,
    output_filename: str = "backtest_results.png"
):
    """
    Run the complete backtesting workflow.
    
    Args:
        initial_capital: Starting capital for the strategy
        rebalance_days: Days between rebalancing
        output_filename: Name of the output plot file (saved in backtesting folder)
    """
    logger.info("=" * 60)
    logger.info("Starting Backtesting Workflow")
    logger.info("=" * 60)
    
    # Step 1: Clean data
    logger.info("\n📊 Step 1: Cleaning and filtering data...")
    df_cleaned = clean_data()
    
    if df_cleaned.empty:
        logger.error("No data available after cleaning. Exiting.")
        return None
    
    # Step 2: Calculate indicators
    logger.info("\n📈 Step 2: Calculating technical indicators...")
    df_with_indicators = calculate_indicators(df_cleaned)
    
    # Step 3: Backtest strategy
    logger.info("\n🎯 Step 3: Running backtest strategy...")
    portfolio_df = backtest_strategy(
        df_with_indicators,
        initial_capital=initial_capital,
        rebalance_days=rebalance_days
    )
    
    if portfolio_df.empty:
        logger.error("Backtest produced no results. Exiting.")
        return None
    
    # Step 4: Calculate performance metrics
    logger.info("\n📊 Step 4: Calculating performance metrics...")
    metrics = calculate_performance_metrics(portfolio_df, initial_capital=initial_capital)
    
    # Step 5: Visualize results
    logger.info("\n📈 Step 5: Generating visualizations...")
    output_path = BACKTESTING_DIR / output_filename
    plot_backtest_results(portfolio_df, str(output_path))
    
    logger.info("\n✅ Backtesting complete!")
    logger.info(f"Results saved to: {output_path}")
    
    return {
        'portfolio_df': portfolio_df,
        'metrics': metrics
    }


if __name__ == '__main__':
    # Run backtest with default parameters
    results = run_backtest(
        initial_capital=10000,
        rebalance_days=7,
        output_filename="backtest_results.png"
    )

