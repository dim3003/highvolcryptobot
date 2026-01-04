# Need to run CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; for the uid generator to work in psql
CREATE_CONTRACTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS contracts(
    uid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    token_address TEXT NOT NULL UNIQUE
)
"""

INSERT_CONTRACTS_SQL = """
INSERT INTO contracts(token_address)
VALUES %s
ON CONFLICT (token_address) DO NOTHING;
"""

SELECT_COUNT_CONTRACTS = """
SELECT COUNT(*) FROM contracts;
"""

SELECT_CONTRACTS_SQL = """
SELECT token_address FROM contracts;
"""

CREATE_PRICES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS prices(
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
CREATE INDEX IF NOT EXISTS idx_prices_token_address ON prices(token_address)
"""

CREATE_PRICES_INDEX_TIMESTAMP_SQL = """
CREATE INDEX IF NOT EXISTS idx_prices_timestamp ON prices(timestamp)
"""

INSERT_PRICES_SQL = """
INSERT INTO prices(token_address, value, timestamp, market_cap, total_volume)
VALUES %s
ON CONFLICT (token_address, timestamp) DO UPDATE SET
    value = EXCLUDED.value,
    market_cap = EXCLUDED.market_cap,
    total_volume = EXCLUDED.total_volume;
"""
