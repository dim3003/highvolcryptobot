import logging
import psycopg2
import pandas as pd
from psycopg2.extensions import connection as Connection
from psycopg2.extras import execute_values
from psycopg2 import sql
from typing import List
from src.sql.public import (
    CREATE_CONTRACTS_TABLE_SQL,
    INSERT_CONTRACTS_SQL,
    SELECT_CONTRACTS_SQL,
)

logger = logging.getLogger(__name__)

class DBService:
    def __init__(self, conn: Connection):
        self.conn = conn

    # --- Tokens ---
    def store_tokens(self, tokens: List[str]):
        rows = [(t,) for t in tokens]
        try:
            with self.conn.cursor() as curs:
                curs.execute(CREATE_CONTRACTS_TABLE_SQL)
                execute_values(curs, INSERT_CONTRACTS_SQL, rows)
            self.conn.commit()
            logger.info("Inserted %d tokens", len(tokens))
        except Exception as e:
            self.conn.rollback()
            logger.exception("Failed to insert tokens")
            raise e

    def get_tokens(self):
        try:
            with self.conn.cursor() as curs:
                curs.execute(SELECT_CONTRACTS_SQL)
                return [row[0] for row in curs.fetchall()]
        except Exception:
            logger.exception("Failed to select contract addresses")
            raise

    # --- Prices ---
    def store_prices(self, token_address: str, prices: List[dict], schema: str="backtest"):
        """
        Store daily price data for a token.
        
        Args:
            token_address: The token contract address
            prices: List of price dictionaries with keys: value, timestamp, marketCap, totalVolume
        """
        rows = [
            (
                token_address,
                price.get("value"),
                price.get("timestamp"),
                price.get("marketCap"),
                price.get("totalVolume"),
            )
            for price in prices
        ]
        try:
            with self.conn.cursor() as curs:
                curs.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema)))
                curs.execute(
                    sql.SQL("""
                        CREATE TABLE IF NOT EXISTS {}.prices(
                            uid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                            token_address TEXT NOT NULL,
                            value NUMERIC NOT NULL,
                            timestamp TIMESTAMPTZ NOT NULL,
                            market_cap NUMERIC,
                            total_volume NUMERIC,
                            created_at TIMESTAMPTZ DEFAULT NOW(),
                            UNIQUE(token_address, timestamp)
                        )
                    """).format(sql.Identifier(schema))
                )
                curs.execute(
                    sql.SQL("""
                        CREATE INDEX IF NOT EXISTS idx_prices_token_address ON {}.prices(token_address)
                    """).format(sql.Identifier(schema))
                )
                curs.execute(
                    sql.SQL("""
                        CREATE INDEX IF NOT EXISTS idx_prices_timestamp ON {}.prices(timestamp)
                    """).format(sql.Identifier(schema))
                )
                execute_values(
                    curs,
                    sql.SQL("""
                        INSERT INTO {}.prices(token_address, value, timestamp, market_cap, total_volume)
                        VALUES %s
                        ON CONFLICT (token_address, timestamp) DO UPDATE SET
                            value = EXCLUDED.value,
                            market_cap = EXCLUDED.market_cap,
                            total_volume = EXCLUDED.total_volume;
                    """).format(sql.Identifier(schema)),
                    rows)
            self.conn.commit()
            logger.info("Inserted %d prices for token %s", len(prices), token_address)
        except Exception as e:
            self.conn.rollback()
            logger.exception("Failed to insert prices")
            raise e

    def get_prices(self, schema: str="backtest"):
        try:
            with self.conn.cursor() as curs:
                curs.execute(
                    sql.SQL("""
                        SELECT * FROM {}.prices;
                    """).format(sql.Identifier(schema))
                )
                rows = curs.fetchall()
                df = pd.DataFrame(rows, columns=[
                    'uid', 'token_address', 'value', 'timestamp',
                    'market_cap', 'total_volume', 'created_at'
                ])
                # Convert to strings
                df['uid'] = df['uid'].astype(str)
                df['token_address'] = df['token_address'].astype(str)
                # Convert strings to numeric
                df['value'] = df['value'].astype(float)
                df['market_cap'] = df['market_cap'].astype(float)
                df['total_volume'] = df['total_volume'].astype(float)
                # Convert timestamp strings to datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
                df['created_at'] = pd.to_datetime(df['created_at'], utc=True)
                return df
        except Exception:
            logger.exception("Failed to get all crypto prices")
            raise

