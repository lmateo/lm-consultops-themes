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
