import psycopg2
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
        
        # Check quality for remaining tokens
        check_data_quality(df_cleaned)
        
        return df_cleaned

def apply_quality_filters(df):
    """Remove tokens that don't meet quality criteria"""
    tokens_to_keep = []
    
    for token_addr in df['token_address'].unique():
        token_data = df[df['token_address'] == token_addr].sort_values('timestamp')
        
        # Criteria 1: Average market cap >= 1,000,000
        avg_mcap = token_data['market_cap'].mean()
        if avg_mcap < 1_000_000:
            print(f"❌ Removing {token_addr[:10]}... - Low market cap: ${avg_mcap:,.0f}")
            continue
        
        # Criteria 2: At least 730 data rows
        if len(token_data) < 730:
            print(f"❌ Removing {token_addr[:10]}... - Insufficient data: {len(token_data)} rows")
            continue
        
        # Criteria 3: No intraday changes > 300%
        price_changes = token_data['value'].pct_change().abs()
        max_change = price_changes.max()
        if max_change > 3.0:  # 300% = 3.0
            print(f"❌ Removing {token_addr[:10]}... - Extreme volatility: {max_change*100:.1f}%")
            continue
        
        # Token passes all criteria
        tokens_to_keep.append(token_addr)
        print(f"✅ Keeping {token_addr[:10]}... - MCap: ${avg_mcap:,.0f}, Rows: {len(token_data)}, Max change: {max_change*100:.1f}%")
    
    # Filter dataframe to only include good tokens
    df_cleaned = df[df['token_address'].isin(tokens_to_keep)]
    return df_cleaned

def check_data_quality(df):
    """Print summary stats for each token"""
    print("\n=== DATA QUALITY CHECK ===\n")
    
    for token_addr in df['token_address'].unique():
        token_data = df[df['token_address'] == token_addr]
        
        print(f"Token: {token_addr}")
        print(f"  Count: {len(token_data)}")
        print(f"  Min: ${token_data['value'].min():.6f}")
        print(f"  Max: ${token_data['value'].max():.6f}")
        print(f"  Mean: ${token_data['value'].mean():.6f}")
        print(f"  Std Dev: {token_data['value'].std():.6f}")
        print(f"  Average MCap: ${token_data['market_cap'].mean():,.2f}")
        
        # Check for zeros or negatives
        if (token_data['value'] <= 0).any():
            print(f"  ⚠️  WARNING: Has zero or negative values!")
        
        # Check for huge jumps
        token_sorted = token_data.sort_values('timestamp')
        price_changes = token_sorted['value'].pct_change().abs()
        max_change = price_changes.max()
        if max_change > 2:  # 200% change
            print(f"  ⚠️  WARNING: Large price jump detected: {max_change*100:.1f}%")
        
        print()

if __name__ == '__main__':
    clean_data()
