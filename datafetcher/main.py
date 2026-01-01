import os
import logging
from typing import Generator
import requests
import psycopg2
from psycopg2.extensions import connection as Connection
from psycopg2.extras import execute_values
from datafetcher.sql import CREATE_TOKENS_TABLE_SQL, INSERT_TOKENS_SQL

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = os.environ["ONEINCH_API_KEY"]
CHAIN_ID = 42161  # Arbitrum One

URL = f"https://api.1inch.dev/swap/v6.1/{CHAIN_ID}/tokens"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "accept": "application/json",
}

def get_available_tokens() -> Generator[str, None, None]:
    """
    Fetch available tokens from the 1inch API.
    
    Yields:
        token addresses as strings
    """
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    try:
        tokens = data["tokens"]
    except KeyError:
        raise RuntimeError("Unexpected API response: missing 'tokens' key")
    
    for addr in tokens.keys():
        yield addr

def store_tokens_postgres(conn: Connection, tokens: list[str]) -> None:
    """
    Store a list of token addresses in Postgres.

    Each token gets its own row in the table 'tokens'.

    Args:
        conn: psycopg2 database connection
        tokens: list of token addresses as strings
    """
    rows = [(t,) for t in tokens]

    try:
        with conn.cursor() as curs:
            curs.execute(CREATE_TOKENS_TABLE_SQL)
            execute_values(curs, INSERT_TOKENS_SQL, rows)
        conn.commit()
        logger.info("Inserted %d tokens into the database", len(tokens))
    except Exception as e:
        conn.rollback()
        logger.exception("Failed to insert tokens into the database")
        raise e

