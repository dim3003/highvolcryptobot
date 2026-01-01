import re
from datafetcher.main import get_available_tokens, store_tokens_postgres
from unittest.mock import MagicMock

ETH_ADDRESS_REGEX = re.compile(r"^0x[a-fA-F0-9]{40}$")

def test_get_available_tokens_format(mocker):
    fake_response = mocker.Mock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {
        "tokens": {
            "0x32eb7902d4134bf98a28b963d26de779af92a212": {},
            "0x539bde0d7dbd336b79148aa742883198bbf60342": {},
        }
    }

    mocker.patch(
        "datafetcher.main.requests.get",
        return_value=fake_response,
    )

    tokens = list(get_available_tokens())

    assert isinstance(tokens, list)
    assert len(tokens) > 0

    for token in tokens:
        assert isinstance(token, str)
        assert ETH_ADDRESS_REGEX.match(token)

    assert len(tokens) == len(set(tokens))

def test_store_tokens_postgres(mocker):
    # Sample token addresses
    tokens = [
        "0x32eb7902d4134bf98a28b963d26de779af92a212",
        "0x539bde0d7dbd336b79148aa742883198bbf60342",
    ]

    # --- Mock Postgres connection ---
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.connection.encoding = 'UTF8'
    def mogrify_side_effect(template, args):
        # Simply return a bytes string for testing purposes
        return b"(" + b",".join(str(a).encode() for a in args) + b")"
    mock_cursor.mogrify.side_effect = mogrify_side_effect
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Patch execute_values so we can track its call
    mock_execute_values = mocker.patch(
        "datafetcher.main.execute_values"
    )

    # Call the function
    store_tokens_postgres(mock_conn, tokens)

    # Assert table creation was called
    create_table_call = mock_cursor.execute.call_args_list[0][0][0]
    assert "CREATE TABLE IF NOT EXISTS tokens" in create_table_call

    # Assert execute_values was called with the token addresses
    values_arg = mock_execute_values.call_args[0][2]
    assert values_arg == [(t,) for t in tokens]

    # Assert commit was called
    mock_conn.commit.assert_called()
