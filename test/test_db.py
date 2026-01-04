import pytest
from unittest.mock import MagicMock
from src.data.db import DBService
from psycopg2.extras import execute_values
from src.sql import (
    INSERT_CONTRACTS_SQL,
    CREATE_CONTRACTS_TABLE_SQL,
    SELECT_CONTRACTS_SQL,
    CREATE_PRICES_TABLE_SQL,
    CREATE_PRICES_INDEX_TOKEN_SQL,
    CREATE_PRICES_INDEX_TIMESTAMP_SQL,
    INSERT_PRICES_SQL,
)

def test_dbservice_store_tokens(mocker):
    # Sample token addresses
    tokens = [
        "0x32eb7902d4134bf98a28b963d26de779af92a212",
        "0x539bde0d7dbd336b79148aa742883198bbf60342",
    ]

    # --- Mock Postgres connection and cursor ---
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.connection.encoding = 'UTF8'
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Patch execute_values to track its calls
    mock_execute_values = mocker.patch("src.data.db.execute_values")

    # Create DBService instance with mock connection
    db_service = DBService(mock_conn)

    # Call store_tokens
    db_service.store_tokens(tokens)

    # --- Assertions ---
    # 1. Table creation executed
    create_table_call = mock_cursor.execute.call_args_list[0][0][0]
    assert CREATE_CONTRACTS_TABLE_SQL in create_table_call

    # 2. execute_values called with correct rows
    expected_rows = [(t,) for t in tokens]
    insert_sql_arg = mock_execute_values.call_args[0][1]
    values_arg = mock_execute_values.call_args[0][2]
    assert insert_sql_arg == INSERT_CONTRACTS_SQL
    assert values_arg == expected_rows

    # 3. Commit called
    mock_conn.commit.assert_called()

def test_dbservice_get_tokens(mocker):
    # --- Mock Postgres connection and cursor ---
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.connection.encoding = 'UTF8'
    mock_cursor.fetchall.return_value = [
        ('0x32eb7902d4134bf98a28b963d26de779af92a212',),
        ('0x539bde0d7dbd336b79148aa742883198bbf60342',)
    ]
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Create DBService instance with mock connection
    db_service = DBService(mock_conn)

    # Call store_tokens
    result = db_service.get_tokens()

    # --- Assertions ---
    # 1. Check that the correct SQL was used
    get_contracts_call = mock_cursor.execute.call_args_list[0][0][0]
    assert SELECT_CONTRACTS_SQL in get_contracts_call 

    # 2. Check that the returned list is correct
    assert result == [
        "0x32eb7902d4134bf98a28b963d26de779af92a212",
        "0x539bde0d7dbd336b79148aa742883198bbf60342",
    ]

def test_dbservice_store_prices(mocker):
    # Sample price data matching the structure from the API
    prices = [
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
    token_address = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"

    # --- Mock Postgres connection and cursor ---
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.connection.encoding = 'UTF8'
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Patch execute_values to track its calls
    mock_execute_values = mocker.patch("src.data.db.execute_values")

    # Create DBService instance with mock connection
    db_service = DBService(mock_conn)

    # Call store_prices
    db_service.store_prices(token_address, prices)

    # --- Assertions ---
    # 1. Table creation and indexes executed
    create_table_call = mock_cursor.execute.call_args_list[0][0][0]
    assert CREATE_PRICES_TABLE_SQL.strip() in create_table_call
    create_index_token_call = mock_cursor.execute.call_args_list[1][0][0]
    assert CREATE_PRICES_INDEX_TOKEN_SQL.strip() in create_index_token_call
    create_index_timestamp_call = mock_cursor.execute.call_args_list[2][0][0]
    assert CREATE_PRICES_INDEX_TIMESTAMP_SQL.strip() in create_index_timestamp_call

    # 2. execute_values called with correct data
    insert_sql_arg = mock_execute_values.call_args[0][1]
    values_arg = mock_execute_values.call_args[0][2]
    assert INSERT_PRICES_SQL in insert_sql_arg
    
    # Verify the data structure matches expected format
    # Each row should have: token_address, value, timestamp, market_cap, total_volume
    assert len(values_arg) == len(prices)
    assert values_arg[0][0] == token_address
    assert values_arg[0][1] == "1900.00"
    assert values_arg[0][2] == "2024-01-01T00:00:00Z"
    assert values_arg[0][3] == "274292310008.21802"
    assert values_arg[0][4] == "6715146404.608721"

    # 3. Commit called
    mock_conn.commit.assert_called()
