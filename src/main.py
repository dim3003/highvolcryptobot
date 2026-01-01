import psycopg2
from src.db import DBService
from src.fetcher import get_available_tokens
from .db_config import DB_CONFIG
from .sql import CREATE_CONTRACTS_TABLE_SQL, SELECT_COUNT_CONTRACTS 

def main():
    with psycopg2.connect(**DB_CONFIG) as conn:
        db_service = DBService(conn)

        # Check if tokens table already has data
        with conn.cursor() as curs:            
            curs.execute(CREATE_CONTRACTS_TABLE_SQL)
            curs.execute(SELECT_COUNT_CONTRACTS)
            count = curs.fetchone()[0]

        if count > 0:
            print(f"Tokens already stored ({count} entries). Skipping.")
            return

        # Fetch and store tokens
        tokens = list(get_available_tokens())
        db_service.store_tokens(tokens)
        print(f"Stored {len(tokens)} tokens in the database")

if __name__ == "__main__":
    main()

