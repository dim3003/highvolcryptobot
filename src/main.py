import psycopg2
import logging

# Configure logging FIRST, before importing other modules
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

from src.db import DBService
from src.fetcher import get_available_tokens
from src.historical_prices import fetch_and_store_all_historical_prices
from .db_config import DB_CONFIG
from .sql import CREATE_CONTRACTS_TABLE_SQL, SELECT_COUNT_CONTRACTS 

logger = logging.getLogger(__name__)

def main():
    with psycopg2.connect(**DB_CONFIG) as conn:
        db_service = DBService(conn)

        # Ensure contracts table exists
        with conn.cursor() as curs:            
            curs.execute(CREATE_CONTRACTS_TABLE_SQL)
            curs.execute(SELECT_COUNT_CONTRACTS)
            count_before = curs.fetchone()[0]

        # Fetch and store all tokens (ON CONFLICT handles duplicates)
        logger.info("Fetching and storing all contracts...")
        tokens = list(get_available_tokens())
        db_service.store_tokens(tokens)
        
        with conn.cursor() as curs:
            curs.execute(SELECT_COUNT_CONTRACTS)
            count_after = curs.fetchone()[0]
        
        logger.info(f"Contracts: {count_before} -> {count_after} (stored {len(tokens)} new tokens)")

        # Fetch and store all historical prices for all contracts
        logger.info("Fetching and storing all historical prices...")
        fetch_and_store_all_historical_prices(db_service)
        logger.info("Completed fetching and storing all historical prices.")

if __name__ == "__main__":
    main()

