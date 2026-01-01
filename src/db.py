import logging
import psycopg2
from psycopg2.extensions import connection as Connection
from psycopg2.extras import execute_values
from typing import List
from .sql import (
    CREATE_CONTRACTS_TABLE_SQL,
    INSERT_CONTRACTS_SQL,
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
