import base64
import hashlib
import hmac
import json
import time


def _encode_payload(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _decode_payload(encoded_payload: str) -> dict:
    padding = "=" * (-len(encoded_payload) % 4)
    raw = base64.urlsafe_b64decode(f"{encoded_payload}{padding}".encode("utf-8"))
    return json.loads(raw.decode("utf-8"))


def create_download_token(
    *,
    secret_key: str,
    purchase_id: int,
    template_slug: str,
    customer_email: str,
    expires_in_seconds: int = 3600,
) -> str:
    payload = {
        "purchase_id": purchase_id,
        "template_slug": template_slug,
        "customer_email": customer_email.lower().strip(),
        "exp": int(time.time()) + expires_in_seconds,
    }
    encoded_payload = _encode_payload(payload)
    signature = hmac.new(
        secret_key.encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{encoded_payload}.{signature}"


def verify_download_token(token: str, *, secret_key: str) -> dict | None:
    if "." not in token:
        return None

    encoded_payload, provided_signature = token.split(".", 1)
    expected_signature = hmac.new(
        secret_key.encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(provided_signature, expected_signature):
        return None

    try:
        payload = _decode_payload(encoded_payload)
    except (json.JSONDecodeError, ValueError):
        return None

    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload
