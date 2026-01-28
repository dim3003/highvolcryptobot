# src/bot/check_tokens.py
import psycopg2

import src.data as data
from src.db_config import DB_CONFIG


def check_new_tokens() -> list[str]:
    api_tokens = list(dict.fromkeys(data.get_available_tokens()))  # dedup, keep order

    with psycopg2.connect(**DB_CONFIG) as conn:
        db_service = data.DBService(conn)
        db_tokens = set(db_service.get_tokens())

        new_tokens = [t for t in api_tokens if t not in db_tokens]
        if new_tokens:
            db_service.store_tokens(new_tokens)

    return new_tokens
