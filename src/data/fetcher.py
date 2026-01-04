import os
import time
import requests
import logging
from typing import Generator
from datetime import datetime
from typing import Union
from src.config import oneinch_settings, alchemy_settings

logger = logging.getLogger(__name__)

# Rate limiting: 300 requests per hour = 1 request per 12 seconds
# Use 13 seconds to be safe
MIN_REQUEST_INTERVAL = 13  # seconds
_last_request_time = 0

def get_available_tokens() -> Generator[str, None, None]:
    """
        Fetch available token addresses from 1inch and yield them one by one.

        Yields:
            str: The token address as a string.

        Raises:
        RuntimeError: If the API response does not contain a 'tokens' key.
        requests.HTTPError: If the API request fails.
    """
    resp = requests.get(oneinch_settings.get_tokens_url, headers=oneinch_settings.headers)
    resp.raise_for_status()
    data = resp.json()
    tokens = data.get("tokens")
    if not tokens:
        raise RuntimeError("Unexpected API response: missing 'tokens' key")
    for addr in tokens.keys():
        yield addr


def _rate_limit():
    """Ensure we don't exceed the API rate limit (300 requests/hour)."""
    global _last_request_time
    current_time = time.time()
    time_since_last = current_time - _last_request_time
    
    if time_since_last < MIN_REQUEST_INTERVAL:
        wait_time = MIN_REQUEST_INTERVAL - time_since_last
        logger.info(f"Rate limiting: waiting {wait_time:.2f} seconds to respect API limit (300 req/hour)")
        time.sleep(wait_time)
    
    _last_request_time = time.time()


def get_token_prices(
    network: str = "eth-mainnet",
    address: str = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
    start: Union[datetime, float] = 1704067200,
    end: Union[datetime, float] = 1706745599,
    max_retries: int = 3,
    retry_delay: int = 60,
) -> Generator[dict, None, None]:
    """
    Yield historical token prices from the API.

    Args:
        network (str): Network identifier (default "eth-mainnet").
        address (str): Token contract address (default USDC).
        start (datetime | float): Start time (datetime or epoch timestamp).
        end (datetime | float): End time (datetime or epoch timestamp).
        max_retries (int): Maximum number of retries for rate limit errors (default 3).
        retry_delay (int): Delay in seconds before retrying after rate limit (default 60).

    Yields:
        dict: A dictionary representing a price point.
    """
    # Convert timestamps to ISO 8601 if needed
    def to_iso(dt: Union[datetime, float]) -> str:
        if isinstance(dt, float) or isinstance(dt, int):
            return datetime.utcfromtimestamp(dt).isoformat() + "Z"
        return dt.isoformat() + "Z"

    payload = {
        "network": network,
        "address": address,
        "startTime": to_iso(start),
        "endTime": to_iso(end),
        "interval": "1d",
        "withMarketData": True
    }

    # Apply rate limiting
    _rate_limit()

    resp = None
    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(
                alchemy_settings.get_token_historical_prices_url,
                json=payload,
                headers=alchemy_settings.headers
            )
            logger.debug(f"Status code: {resp.status_code}")
            logger.debug(f"Response body: {resp.text}")
            
            # Handle rate limit errors
            if resp.status_code == 429:
                error_data = resp.json() if resp.text else {}
                error_msg = error_data.get("error", {}).get("message", "Rate limit exceeded")
                
                if attempt < max_retries:
                    wait_time = retry_delay * (attempt + 1)  # Exponential backoff
                    logger.warning(
                        f"Rate limit exceeded (429). Waiting {wait_time} seconds before retry "
                        f"({attempt + 1}/{max_retries}). Error: {error_msg}"
                    )
                    time.sleep(wait_time)
                    # Reset rate limiter after waiting
                    global _last_request_time
                    _last_request_time = time.time()
                    continue
                else:
                    logger.error(f"Rate limit exceeded after {max_retries} retries. Error: {error_msg}")
                    resp.raise_for_status()
            
            resp.raise_for_status()
            
            # Success - break out of retry loop
            break
            
        except requests.exceptions.HTTPError as e:
            # Check if it's a 429 error and we can retry
            if resp and resp.status_code == 429 and attempt < max_retries:
                continue  # Will retry (already handled above, but catch here too)
            raise  # Re-raise if not a retryable error or out of retries

    response_json = resp.json()
    
    # Check if 'data' key exists in response
    if "data" not in response_json:
        raise RuntimeError("Unexpected API response: missing 'data' key")
    
    data = response_json.get("data")
    
    # Handle case where data is directly an array (empty or with prices)
    if isinstance(data, list):
        # If data is an empty array, just return (no prices available)
        if not data:
            logger.debug(f"No price data available for token {address}")
            return
        # If data is a list of prices, yield them directly
        prices = data
    elif isinstance(data, dict):
        # Handle case where data is a dict with 'prices' key
        prices = data.get("prices")
        if prices is None:
            raise RuntimeError("Unexpected API response: 'data' object missing 'prices' key")
        if not prices:
            logger.debug(f"No price data available for token {address}")
            return
    else:
        raise RuntimeError(f"Unexpected API response: 'data' has unexpected type: {type(data)}")

    for price in prices:
        yield price
