"""Backtesting framework for trading strategies."""

from .data_cleaner import clean_data, apply_quality_filters
from .indicators import calculate_indicators, calculate_rsi
from .performance import calculate_performance_metrics
from .plot import plot_backtest_results
from .stablecoins import ARBITRUM_STABLECOINS

__all__ = [
    'run_backtest',
    'backtest_strategy',
    'clean_data',
    'apply_quality_filters',
    'calculate_indicators',
    'calculate_rsi',
    'calculate_performance_metrics',
    'plot_backtest_results',
    'ARBITRUM_STABLECOINS',
]
