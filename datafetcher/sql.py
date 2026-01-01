CREATE_TOKENS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tokens(
    uid TEXT PRIMARY KEY,
    token_address TEXT
)
"""

INSERT_TOKENS_SQL = "INSERT INTO tokens (uid, token_address) VALUES %s"

