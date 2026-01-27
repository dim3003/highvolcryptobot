CREATE_BACKTEST_SCHEMA= """
CREATE SCHEMA IF NOT EXISTS backtest;
"""

CREATE_PRICES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS backtest.prices(
    uid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    token_address TEXT NOT NULL,
    value TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    market_cap TEXT,
    total_volume TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(token_address, timestamp)
)
"""

CREATE_PRICES_INDEX_TOKEN_SQL = """
CREATE INDEX IF NOT EXISTS idx_prices_token_address ON backtest.prices(token_address)
"""

CREATE_PRICES_INDEX_TIMESTAMP_SQL = """
CREATE INDEX IF NOT EXISTS idx_prices_timestamp ON backtest.prices(timestamp)
"""

INSERT_PRICES_SQL = """
INSERT INTO backtest.prices(token_address, value, timestamp, market_cap, total_volume)
VALUES %s
ON CONFLICT (token_address, timestamp) DO UPDATE SET
    value = EXCLUDED.value,
    market_cap = EXCLUDED.market_cap,
    total_volume = EXCLUDED.total_volume;
"""

SELECT_ALL_PRICES_SQL = """
SELECT * FROM backtest.prices;
"""

CREATE_CLEAN_PRICES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS backtest.clean_prices(
    uid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    token_address TEXT NOT NULL,
    value TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    market_cap TEXT,
    total_volume TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    volatility TEXT, 
    UNIQUE(token_address, timestamp)
)
"""

CREATE_CLEAN_PRICES_INDEX_TOKEN_SQL = """
CREATE INDEX IF NOT EXISTS idx_clean_prices_token_address 
ON backtest.clean_prices(token_address);
"""

CREATE_CLEAN_PRICES_INDEX_TIMESTAMP_SQL = """
CREATE INDEX IF NOT EXISTS idx_clean_prices_timestamp 
ON backtest.clean_prices(timestamp);
"""

INSERT_CLEAN_PRICES_SQL = """
INSERT INTO backtest.clean_prices(token_address, value, timestamp, market_cap, total_volume, volatility)
VALUES %s
ON CONFLICT (token_address, timestamp) DO UPDATE SET
    value = EXCLUDED.value,
    market_cap = EXCLUDED.market_cap,
    total_volume = EXCLUDED.total_volume;

"""
