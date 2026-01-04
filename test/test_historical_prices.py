import pytest
from unittest.mock import MagicMock
from datetime import datetime
from src.data.db import DBService


def test_fetch_and_store_all_historical_prices(mocker):
    """
    Test that the function fetches all tokens from DB,
    gets historical prices for each, and stores them.
    """
    # Sample tokens from database
    tokens = [
        "0x32eb7902d4134bf98a28b963d26de779af92a212",
        "0x539bde0d7dbd336b79148aa742883198bbf60342",
    ]
    
    # Sample price data for each token
    prices_token1 = [
        {
            "value": "1900.00",
            "timestamp": "2024-01-01T00:00:00Z",
            "marketCap": "274292310008.21802",
            "totalVolume": "6715146404.608721"
        },
        {
            "value": "1950.50",
            "timestamp": "2024-01-02T00:00:00Z",
            "marketCap": "280000000000.00",
            "totalVolume": "7000000000.00"
        }
    ]
    
    prices_token2 = [
        {
            "value": "1.00",
            "timestamp": "2024-01-01T00:00:00Z",
            "marketCap": "1000000000.00",
            "totalVolume": "50000000.00"
        }
    ]

    # --- Mock DB connection and service ---
    mock_conn = MagicMock()
    db_service = DBService(mock_conn)
    
    # Mock get_tokens to return our sample tokens
    mocker.patch.object(db_service, 'get_tokens', return_value=tokens)
    
    # Mock store_prices to track calls
    mock_store_prices = mocker.patch.object(db_service, 'store_prices')
    
    # Mock get_token_prices to return different prices for different tokens
    def mock_get_token_prices(network, address, start, end):
        if address == tokens[0]:
            return iter(prices_token1)
        elif address == tokens[1]:
            return iter(prices_token2)
        return iter([])
    
    mock_get_prices = mocker.patch('src.data.historical_prices.get_token_prices', side_effect=mock_get_token_prices)
    
    # Import and call the function
    from src.data.historical_prices import fetch_and_store_all_historical_prices
    fetch_and_store_all_historical_prices(db_service)
    
    # --- Assertions ---
    # 1. get_tokens was called
    db_service.get_tokens.assert_called_once()
    
    # 2. get_token_prices was called for each token
    assert mock_get_prices.call_count == len(tokens)
    
    # 3. store_prices was called for each token with correct data
    assert mock_store_prices.call_count == len(tokens)
    
    # Check first token prices were stored correctly
    call_args_token1 = mock_store_prices.call_args_list[0]
    assert call_args_token1[0][0] == tokens[0]
    assert call_args_token1[0][1] == prices_token1
    
    # Check second token prices were stored correctly
    call_args_token2 = mock_store_prices.call_args_list[1]
    assert call_args_token2[0][0] == tokens[1]
    assert call_args_token2[0][1] == prices_token2


def test_fetch_and_store_all_historical_prices_with_empty_tokens(mocker):
    """
    Test that the function handles empty token list gracefully.
    """
    # --- Mock DB connection and service ---
    mock_conn = MagicMock()
    db_service = DBService(mock_conn)
    
    # Mock get_tokens to return empty list
    mocker.patch.object(db_service, 'get_tokens', return_value=[])
    
    # Mock store_prices to track calls
    mock_store_prices = mocker.patch.object(db_service, 'store_prices')
    
    # Import and call the function
    from src.data.historical_prices import fetch_and_store_all_historical_prices
    fetch_and_store_all_historical_prices(db_service)
    
    # --- Assertions ---
    # get_tokens was called
    db_service.get_tokens.assert_called_once()
    
    # store_prices was never called
    mock_store_prices.assert_not_called()


def test_fetch_and_store_all_historical_prices_with_date_range(mocker):
    """
    Test that the function uses the correct date range for fetching prices.
    """
    tokens = ["0x32eb7902d4134bf98a28b963d26de779af92a212"]
    prices = [
        {
            "value": "1900.00",
            "timestamp": "2024-01-01T00:00:00Z",
            "marketCap": "274292310008.21802",
            "totalVolume": "6715146404.608721"
        }
    ]
    
    # --- Mock DB connection and service ---
    mock_conn = MagicMock()
    db_service = DBService(mock_conn)
    
    mocker.patch.object(db_service, 'get_tokens', return_value=tokens)
    mocker.patch.object(db_service, 'store_prices')
    
    mock_get_prices = mocker.patch(
        'src.data.historical_prices.get_token_prices',
        return_value=iter(prices)
    )
    
    # Import and call the function
    from src.data.historical_prices import fetch_and_store_all_historical_prices
    
    # Test with custom date range
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2024, 12, 31)
    fetch_and_store_all_historical_prices(db_service, start_date=start_date, end_date=end_date)
    
    # Verify get_token_prices was called with correct date range
    call_args = mock_get_prices.call_args
    assert call_args[1]['start'] == start_date
    assert call_args[1]['end'] == end_date

