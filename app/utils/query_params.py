from typing import Annotated
from urllib.parse import urlencode

from fastapi import Query
from pydantic import BeforeValidator


def coerce_optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


OptionalFloatQuery = Annotated[float | None, BeforeValidator(coerce_optional_float), Query()]


def build_query_string(**params: object) -> str:
    cleaned = {key: value for key, value in params.items() if value not in (None, "")}
    return urlencode(cleaned)


def query_string_filter(params: dict[str, object]) -> str:
    return build_query_string(**params)


def format_compact_number(value: object) -> str:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return "0"
    if number >= 1_000_000:
        formatted = f"{number / 1_000_000:.1f}".rstrip("0").rstrip(".")
        return f"{formatted}M"
    if number >= 1_000:
        formatted = f"{number / 1_000:.1f}".rstrip("0").rstrip(".")
        return f"{formatted}K"
    return str(number)


def build_page_urls(base_path: str, page_count: int, current_page: int, **params: object) -> list[dict[str, object]]:
    links: list[dict[str, object]] = []
    for page_num in range(1, page_count + 1):
        links.append(
            {
                "page": page_num,
                "url": f"{base_path}?{build_query_string(page=page_num, **params)}",
                "current": page_num == current_page,
            }
        )
    return links
