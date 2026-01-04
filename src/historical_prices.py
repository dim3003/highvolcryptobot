import logging
from datetime import datetime, timedelta
from typing import Optional
from src.db import DBService
from src.fetcher import get_token_prices

logger = logging.getLogger(__name__)

# Default date range: from Ethereum launch (2015-07-30) to now
# This should cover the "furthest possible" historical data
DEFAULT_START_DATE = datetime(2015, 7, 30)
DEFAULT_END_DATE = datetime.now()

# API limit: maximum days per request
MAX_DAYS_PER_REQUEST = 365


def fetch_and_store_all_historical_prices(
    db_service: DBService,
    network: str = "arb-mainnet",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> None:
    """
    Fetch and store all historical prices for all tokens in the contracts table.
    
    Args:
        db_service: DBService instance with active database connection
        network: Network identifier (default "eth-mainnet")
        start_date: Start date for historical prices (default: Ethereum launch date)
        end_date: End date for historical prices (default: current date)
    
    This function:
    1. Gets all token addresses from the contracts table
    2. For each token, fetches historical prices from the API
    3. Stores the prices in the prices table
    """
    # Use default dates if not provided
    if start_date is None:
        start_date = DEFAULT_START_DATE
    if end_date is None:
        end_date = DEFAULT_END_DATE
    
    # Get all tokens from database
    tokens = db_service.get_tokens()
    
    if not tokens:
        logger.info("No tokens found in database. Skipping price fetch.")
        return
    
    logger.info(f"Found {len(tokens)} tokens. Fetching historical prices...")
    
    total_prices_stored = 0
    
    # Process each token
    for token_address in tokens:
        try:
            logger.info(f"Fetching prices for token: {token_address}")
            
            # Collect all prices from all batches
            all_prices = []
            
            # Split into batches of MAX_DAYS_PER_REQUEST days
            current_start = start_date
            batch_num = 1
            
            while current_start < end_date:
                # Calculate batch end date (either MAX_DAYS_PER_REQUEST days later, or end_date, whichever is earlier)
                current_end = min(
                    current_start + timedelta(days=MAX_DAYS_PER_REQUEST - 1),
                    end_date
                )
                
                logger.info(
                    f"Fetching batch {batch_num} for token {token_address}: "
                    f"{current_start.date()} to {current_end.date()}"
                )
                
                # Fetch historical prices for this batch
                batch_prices = list(get_token_prices(
                    network=network,
                    address=token_address,
                    start=current_start,
                    end=current_end
                ))
                
                if batch_prices:
                    all_prices.extend(batch_prices)
                    logger.info(
                        f"Fetched {len(batch_prices)} prices for batch {batch_num} "
                        f"of token {token_address}"
                    )
                
                # Move to next batch
                current_start = current_end + timedelta(days=1)
                batch_num += 1
            
            if all_prices:
                # Store all prices in database
                db_service.store_prices(token_address, all_prices)
                total_prices_stored += len(all_prices)
                logger.info(
                    f"Stored {len(all_prices)} total prices for token {token_address} "
                    f"(from {batch_num - 1} batch{'es' if batch_num > 2 else ''})"
                )
            else:
                logger.warning(f"No prices found for token {token_address}")
                
        except Exception as e:
            logger.error(f"Error processing token {token_address}: {e}")
            # Continue with next token even if one fails
            continue
    
    logger.info(f"Completed. Stored {total_prices_stored} total price records.")
