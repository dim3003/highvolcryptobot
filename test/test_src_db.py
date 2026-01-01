import pytest
from unittest.mock import MagicMock
from src.db import DBService
from psycopg2.extras import execute_values
from src.sql import INSERT_CONTRACTS_SQL, CREATE_CONTRACTS_TABLE_SQL

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
    mock_execute_values = mocker.patch("src.db.execute_values")

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

