CREATE_CONTRACTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS contracts(
    uid TEXT PRIMARY KEY,
    token_address TEXT
)
"""

INSERT_TOKENS_SQL = "INSERT INTO tokens (uid, token_address) VALUES %s"

