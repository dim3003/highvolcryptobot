import psycopg2
import pandas as pd
import numpy as np
from src.data.db import DBService
from src.db_config import DB_CONFIG
from src.backtesting.stablecoins import ARBITRUM_STABLECOINS

def clean_data():
    with psycopg2.connect(**DB_CONFIG) as conn:
        db_service = DBService(conn)
        df = db_service.get_prices()

        # Remove stablecoins
        stablecoin_addresses = list(ARBITRUM_STABLECOINS.keys())
        df = df[~df['token_address'].isin(stablecoin_addresses)]

        print(f"Tokens after stablecoin removal: {df['token_address'].nunique()}")

        # Basic sanity cleanup only
        df = df.dropna(subset=['value', 'market_cap'])
        df = df[df['value'] > 0]

        return df


def apply_quality_filters(df, current_date):
    """
    Time-safe universe selection.
    Uses only information available up to current_date.
    """
    eligible_tokens = []

    for token_addr, token_data in df.groupby('token_address'):
        token_data = token_data[token_data['timestamp'] <= current_date] \
            .sort_values('timestamp')

        # Token must exist by now
        if len(token_data) < 90:
            continue

        # Latest market cap (NO future averaging)
        latest_mcap = token_data['market_cap'].iloc[-1]
        if latest_mcap < 5_000_000:
            continue

        # Liquidity filter (recent)
        recent_volume = token_data['total_volume'].tail(30)
        if (recent_volume == 0).mean() > 0.1:
            continue

        # Recent volatility filter (NO future max)
        recent_returns = token_data['value'].pct_change().tail(30)
        if recent_returns.abs().max() > 2.0:
            continue

        eligible_tokens.append(token_addr)

    return eligible_tokens

