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
