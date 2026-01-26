import pandas as pd
import numpy as np
from src.backtesting.data_cleaner import apply_quality_filters
from src.backtesting.transaction_costs import apply_transaction_costs
from src.backtesting.slippage import slippage_cost


def backtest_strategy(
    df: pd.DataFrame,
    initial_capital: float = 10000,
    rebalance_days: int = 7,
    sma_period: int = 20,
):
    """
    Simple SMA strategy.

    Assumes:
    - df is already cleaned
    - indicators (including SMA) are already calculated
    """

    sma_col = f"sma_{sma_period}"
    if sma_col not in df.columns:
        raise ValueError(f"Required column '{sma_col}' not found in dataframe")

    dates = sorted(df["timestamp"].unique())
    capital = initial_capital
    current_positions = {}
    portfolio_history = []

    last_rebalance_idx = -rebalance_days

    for i, current_date in enumerate(dates):

        # ------------------------
        # Rebalance
        # ------------------------
        if i - last_rebalance_idx >= rebalance_days:
            eligible_tokens = apply_quality_filters(df, current_date)

            today = df[
                (df["timestamp"] == current_date)
                & (df["token_address"].isin(eligible_tokens))
            ][["token_address", "value", sma_col]].dropna()

            selected = today[today["value"] > today[sma_col]]

            current_positions = {}

            if not selected.empty:
                allocation = capital / len(selected)

                for _, row in selected.iterrows():
                    tx_cost = apply_transaction_costs(allocation)
                    entry_price = row["value"] * (1 + tx_cost / allocation)

                    current_positions[row["token_address"]] = {
                        "entry_price": entry_price,
                        "allocation": allocation,
                    }

            last_rebalance_idx = i

        # ------------------------
        # Daily update
        # ------------------------
        daily_return = 0.0
        exits = []

        for token, pos in current_positions.items():
            today_row = df[
                (df["timestamp"] == current_date)
                & (df["token_address"] == token)
            ]

            if i == 0 or today_row.empty:
                continue

            yesterday_row = df[
                (df["timestamp"] == dates[i - 1])
                & (df["token_address"] == token)
            ]

            if yesterday_row.empty:
                continue

            today_price = today_row["value"].iloc[0]
            yesterday_price = yesterday_row["value"].iloc[0]

            pnl = (today_price - pos["entry_price"]) / pos["entry_price"]
            weight = pos["allocation"] / capital

            # Stop-loss
            if pnl < -0.08:
                slippage = slippage_cost(pos["allocation"], pool_liquidity=100_000_000)
                tx_cost = apply_transaction_costs(pos["allocation"]) / pos["allocation"]
                penalty = slippage + tx_cost

                daily_return += ((today_price - yesterday_price) / yesterday_price) * weight
                daily_return -= penalty
                exits.append(token)
            else:
                daily_return += ((today_price - yesterday_price) / yesterday_price) * weight

        for token in exits:
            current_positions.pop(token, None)

        capital *= (1 + daily_return)

        portfolio_history.append(
            {
                "date": current_date,
                "portfolio_value": capital,
                "n_tokens": len(current_positions),
            }
        )

    return pd.DataFrame(portfolio_history)

