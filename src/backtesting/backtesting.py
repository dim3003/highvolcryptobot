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
import random
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from src.backtesting.data_cleaner import clean_data, apply_quality_filters
from src.backtesting.indicators import calculate_indicators
from src.backtesting.performance import calculate_performance_metrics
from src.backtesting.plot import plot_backtest_results
from src.backtesting.transaction_costs import apply_transaction_costs
from src.backtesting.slippage import slippage_cost


def backtest_strategy(df, initial_capital=10000, rebalance_days=7, sma_period=50):
    """
    SIMPLE SMA STRATEGY
    
    Strategy:
    - Each rebalance period, select tokens with price above their SMA (uptrend)
    - Equally allocate capital to selected tokens
    - Rebalance every `rebalance_days`
    - Apply daily stop-loss (-8%) per token
    """
    dates = sorted(df['timestamp'].unique())
    portfolio_values = []
    capital = initial_capital
    current_positions = {}

    print(f"\n=== SMA-{sma_period} STRATEGY ===")
    print(f"Initial Capital: ${initial_capital:,.2f}")
    print(f"Rebalancing: Every {rebalance_days} days")
    print(f"Backtest Period: {dates[0]} to {dates[-1]}")
    print(f"Total Days: {len(dates)}\n")

    last_rebalance = 0

    for i in range(len(dates)):
        current_date = dates[i]
        should_rebalance = (i - last_rebalance) >= rebalance_days
        new_positions = {}
        
        if should_rebalance:
            eligible_tokens = apply_quality_filters(df, current_date)

            if not eligible_tokens:
                continue

            today_data = df[
                (df['timestamp'] == current_date) &
                (df['token_address'].isin(eligible_tokens))
            ][['token_address', 'value', f'sma_{sma_period}']].dropna()

            selected_tokens = today_data[
                today_data['value'] > today_data[f'sma_{sma_period}']
            ]

            new_positions = {}

            if not selected_tokens.empty:
                allocation_per_token = capital / len(selected_tokens)

                for _, row in selected_tokens.iterrows():
                    tx_cost = apply_transaction_costs(allocation_per_token)
                    entry_price = row['value'] * (1 + tx_cost / allocation_per_token)

                    new_positions[row['token_address']] = {
                        'entry_price': entry_price,
                        'allocation': allocation_per_token
                    }

            current_positions = new_positions
            last_rebalance = i


        # Daily portfolio update
        daily_portfolio_return = 0
        tokens_to_exit = []

        for token_addr, position in current_positions.items():
            today_data = df[(df['token_address'] == token_addr) & (df['timestamp'] == current_date)]
            yesterday_data = df[(df['token_address'] == token_addr) & (df['timestamp'] == dates[i-1])] if i > 0 else None

            if len(today_data) == 0 or (yesterday_data is None or len(yesterday_data) == 0):
                continue

            today_price = today_data['value'].values[0]
            yesterday_price = yesterday_data['value'].values[0]

            total_return = (today_price - position['entry_price']) / position['entry_price']

            # Exit rule: daily stop-loss
            if total_return < -0.08:
                slippage_fraction = slippage_cost(position['allocation'], pool_liquidity=100_000_000)
                tx_cost_fraction = apply_transaction_costs(position['allocation']) / position['allocation']
                exit_penalty = slippage_fraction + tx_cost_fraction
                daily_portfolio_return += (today_price - yesterday_price)/yesterday_price * (position['allocation']/capital) - exit_penalty
                tokens_to_exit.append(token_addr)
            else:
                daily_return = (today_price - yesterday_price) / yesterday_price
                daily_portfolio_return += daily_return * (position['allocation']/capital)

        for token in tokens_to_exit:
            if token in current_positions:
                del current_positions[token]

        # Update portfolio value
        capital = capital * (1 + daily_portfolio_return)
        portfolio_values.append({
            'date': current_date,
            'portfolio_value': capital,
            'n_tokens': len(current_positions)
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
