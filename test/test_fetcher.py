import re
from src.fetcher import get_available_tokens
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
        "src.fetcher.requests.get",
        return_value=fake_response,
    )

    tokens = list(get_available_tokens())

    assert isinstance(tokens, list)
    assert len(tokens) > 0

    for token in tokens:
        assert isinstance(token, str)
        assert ETH_ADDRESS_REGEX.match(token)

    assert len(tokens) == len(set(tokens))
