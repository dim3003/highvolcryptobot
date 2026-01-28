import pytest
from unittest.mock import MagicMock

def test_check_new_tokens_inserts_only_missing(mocker):
    """
    If API returns tokens not in DB, store_tokens should be called with only the missing ones,
    and the function should return that list.
    """
    api_tokens = ["0xaaa", "0xbbb", "0xccc"]
    db_tokens = ["0xaaa", "0xbbb"]  # missing 0xccc

    # Mock API token fetch
    mocker.patch("src.data.get_available_tokens", return_value=iter(api_tokens))

    # Mock DB service + connection context manager
    mock_conn = MagicMock()
    mock_connect = mocker.patch("psycopg2.connect", return_value=mock_conn)

    mock_db_service = MagicMock()
    mock_db_service.get_tokens.return_value = db_tokens
    mocker.patch("src.data.DBService", return_value=mock_db_service)

    # Import function under test (adjust module path to where you placed it)
    from src.bot.check_tokens import check_new_tokens

    new_tokens = check_new_tokens()

    assert new_tokens == ["0xccc"]
    mock_db_service.store_tokens.assert_called_once_with(["0xccc"])
    mock_db_service.get_tokens.assert_called_once()
    mock_connect.assert_called_once()


def test_check_new_tokens_no_new_tokens_does_not_insert(mocker):
    """
    If DB already contains all API tokens, store_tokens should not be called,
    and the function should return an empty list.
    """
    api_tokens = ["0xaaa", "0xbbb"]
    db_tokens = ["0xaaa", "0xbbb", "0xccc"]

    mocker.patch("src.data.get_available_tokens", return_value=iter(api_tokens))

    mock_conn = MagicMock()
    mocker.patch("psycopg2.connect", return_value=mock_conn)

    mock_db_service = MagicMock()
    mock_db_service.get_tokens.return_value = db_tokens
    mocker.patch("src.data.DBService", return_value=mock_db_service)

    from src.bot.check_tokens import check_new_tokens

    new_tokens = check_new_tokens()

    assert new_tokens == []
    mock_db_service.store_tokens.assert_not_called()
    mock_db_service.get_tokens.assert_called_once()


def test_check_new_tokens_empty_api_tokens(mocker):
    """
    If the API returns no tokens, nothing should be inserted and an empty list returned.
    """
    mocker.patch("src.data.get_available_tokens", return_value=iter([]))

    mock_conn = MagicMock()
    mocker.patch("psycopg2.connect", return_value=mock_conn)

    mock_db_service = MagicMock()
    mock_db_service.get_tokens.return_value = ["0xaaa"]
    mocker.patch("src.data.DBService", return_value=mock_db_service)

    from src.bot.check_tokens import check_new_tokens

    new_tokens = check_new_tokens()

    assert new_tokens == []
    mock_db_service.store_tokens.assert_not_called()
    mock_db_service.get_tokens.assert_called_once()


def test_check_new_tokens_duplicate_api_tokens_only_inserts_once(mocker):
    """
    If the API returns duplicates, the function should not attempt to insert duplicates.
    (This test will pass if your DB layer ignores duplicates too, but it's better to dedup.)
    """
    api_tokens = ["0xaaa", "0xaaa", "0xbbb"]
    db_tokens = ["0xaaa"]

    mocker.patch("src.data.get_available_tokens", return_value=iter(api_tokens))

    mock_conn = MagicMock()
    mocker.patch("psycopg2.connect", return_value=mock_conn)

    mock_db_service = MagicMock()
    mock_db_service.get_tokens.return_value = db_tokens
    mocker.patch("src.data.DBService", return_value=mock_db_service)

    from src.bot.check_tokens import check_new_tokens

    new_tokens = check_new_tokens()

    # With current implementation, duplicates will be preserved.
    # If you dedup in check_new_tokens, this should be ["0xbbb"].
    assert new_tokens == ["0xbbb"]
    mock_db_service.store_tokens.assert_called_once_with(["0xbbb"])
