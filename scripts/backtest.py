#!/usr/bin/env python3
"""
Main backtesting script.

Orchestrates the complete backtesting workflow:
1. Data cleaning and filtering
2. Technical indicator calculation
3. Strategy backtesting (dynamic per strategy)
4. Performance metrics calculation
5. Results visualization
"""

import sys
from pathlib import Path
import os
import logging
import argparse
import importlib
import pandas as pd
import numpy as np

# ----------------------------------------------------------------------
# Add project root to sys.path so 'src' imports work from scripts/
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # scripts/ -> project root
sys.path.insert(0, str(PROJECT_ROOT))
# ----------------------------------------------------------------------

# Import backtesting utilities from src
from src.backtesting.data_cleaner import clean_data, apply_quality_filters
from src.backtesting.indicators import calculate_indicators
from src.backtesting.performance import calculate_performance_metrics
from src.backtesting.plot import plot_backtest_results
from src.backtesting.transaction_costs import apply_transaction_costs
from src.backtesting.slippage import slippage_cost

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Output directory 
PERFORMANCE_DIR = PROJECT_ROOT / "src" / "backtesting" / "performance"
PERFORMANCE_DIR.mkdir(exist_ok=True)
PLOTS_DIR = PERFORMANCE_DIR / "plots"
METRICS_DIR = PERFORMANCE_DIR / "metrics"
PLOTS_DIR.mkdir(exist_ok=True)
METRICS_DIR.mkdir(exist_ok=True)


# ----------------------------------------------------------------------
def run_backtest(
    strategy_module,
    initial_capital: float = 10000,
    rebalance_days: int = 7,
    output_plot: str = "backtest_results.png",
    metrics_filename: str = None
):
    """
    Run the complete backtesting workflow with a given strategy module.
    
    Args:
        strategy_module: The Python module containing `backtest_strategy(df, ...)`
        initial_capital: Starting capital
        rebalance_days: Days between rebalancing
        output_plot: Plot filename (saved in backtesting/)
        metrics_filename: Optional metrics filename (saved in performance/)
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
    
    # Step 3: Run strategy-specific backtest
    logger.info(f"\n🎯 Step 3: Running backtest strategy: {strategy_module.__name__}...")
    if not hasattr(strategy_module, "backtest_strategy"):
        logger.error(f"Strategy module {strategy_module.__name__} does not have `backtest_strategy` function!")
        return None
    
    portfolio_df = strategy_module.backtest_strategy(
        df_with_indicators,
        initial_capital=initial_capital,
        rebalance_days=rebalance_days
    )
    if portfolio_df.empty:
        logger.error("Backtest produced no results. Exiting.")
        return None
    
    # Step 4: Calculate performance metrics
    logger.info("\n📊 Step 4: Calculating performance metrics...")
    
    metrics = calculate_performance_metrics(
        portfolio_df,
        initial_capital=initial_capital,
        filename=(METRICS_DIR / metrics_filename).as_posix()
    )

    # Step 5: Generate plot
    logger.info("\n📈 Step 5: Generating visualizations...")
    plot_path = PLOTS_DIR / output_plot
    plot_backtest_results(portfolio_df, str(plot_path))
    
    logger.info("\n✅ Backtesting complete!")
    logger.info(f"Plot saved to: {plot_path}")
    if metrics_filename:
        logger.info(f"Metrics saved to: {METRICS_DIR / metrics_filename}")
    
    return {
        "portfolio_df": portfolio_df,
        "metrics": metrics
    }

# ----------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run backtesting workflow with a specific strategy"
    )
    parser.add_argument(
        "strategy_name",
        type=str,
        help="Name of the strategy in src/backtesting/strategies (without .py)"
    )
    parser.add_argument("--capital", type=float, default=10000)
    parser.add_argument("--rebalance", type=int, default=7)

    args = parser.parse_args()

    # Dynamically import the strategy module
    try:
        strategy_module = importlib.import_module(
            f"src.backtesting.strategies.{args.strategy_name}"
        )
    except ModuleNotFoundError:
        logger.error(
            f"Strategy '{args.strategy_name}' not found in src/backtesting/strategies/"
        )
        exit(1)

    # Auto-generate filenames from strategy name
    metrics_filename = f"{args.strategy_name}_metrics.json"
    plot_filename = f"{args.strategy_name}_plot.png"

    # Run the backtest
    run_backtest(
        strategy_module=strategy_module,
        initial_capital=args.capital,
        rebalance_days=args.rebalance,
        output_plot=plot_filename,
        metrics_filename=metrics_filename
    )

