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
