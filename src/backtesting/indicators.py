import pandas as pd
import numpy as np

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
