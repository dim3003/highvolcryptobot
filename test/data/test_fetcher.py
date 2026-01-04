import re
from datetime import datetime
from unittest.mock import MagicMock
from src.data.fetcher import get_available_tokens, get_token_prices

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
        "src.data.fetcher.requests.get",
        return_value=fake_response,
    )

    tokens = list(get_available_tokens())

    assert isinstance(tokens, list)
    assert len(tokens) > 0

    for token in tokens:
        assert isinstance(token, str)
        assert ETH_ADDRESS_REGEX.match(token)

    assert len(tokens) == len(set(tokens))

def test_get_token_prices(mocker):
    fake_response = mocker.Mock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {
        "data": {
            "prices": [
                {
                    "value": "1900.00",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "marketCap": "274292310008.21802",
                    "totalVolume": "6715146404.608721"
                }
            ]
        }
    }

    mock_get = mocker.patch(
        "src.data.fetcher.requests.post",
        return_value=fake_response,
    )

    start = datetime.fromisoformat("2024-01-01T00:00:00")
    end = datetime.fromisoformat("2024-01-31T23:59:59") 

    prices = list(get_token_prices(
        "eth.mainnet",
        "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        start,
        end
    ))

    assert len(prices) == 1

    price = prices[0]
    assert price == {
        "value": "1900.00",
        "timestamp": "2024-01-01T00:00:00Z",
        "marketCap": "274292310008.21802",
        "totalVolume": "6715146404.608721",
    }

    mock_get.assert_called_once()
