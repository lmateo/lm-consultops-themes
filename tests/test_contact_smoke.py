"""Smoke tests for contact form page and /api/contact endpoint."""

import re
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _extract_captcha(html: str) -> tuple[int, int]:
    match = re.search(r'name="captcha_a"\s+value="(\d+)".*name="captcha_b"\s+value="(\d+)"', html, re.DOTALL)
    assert match, "captcha hidden fields not found on contact page"
    return int(match.group(1)), int(match.group(2))


def test_contact_page_loads_with_captcha():
    response = client.get("/contact")
    assert response.status_code == 200
    html = response.text
    assert "Customization Request" in html
    assert 'action="/api/contact"' in html
    assert 'name="website"' in html
    a, b = _extract_captcha(html)
    assert 1 <= a <= 9 and 1 <= b <= 9
    assert f"What is {a} + {b}?" in html


def test_contact_api_rejects_honeypot():
    response = client.post(
        "/api/contact",
        data={
            "name": "Test User",
            "email": "test@example.com",
            "message": "Hello",
            "website": "https://spam.example",
            "captcha_a": 2,
            "captcha_b": 3,
            "captcha_answer": "5",
        },
    )
    assert response.status_code == 400
    assert "Invalid submission" in response.json()["detail"]


def test_contact_api_rejects_wrong_captcha():
    response = client.post(
        "/api/contact",
        data={
            "name": "Test User",
            "email": "test@example.com",
            "message": "Hello",
            "captcha_a": 2,
            "captcha_b": 3,
            "captcha_answer": "99",
        },
    )
    assert response.status_code == 400
    assert "math question" in response.json()["detail"]


def test_contact_api_returns_503_when_not_configured():
    import app.routers.public as public_router

    with (
        patch.object(public_router.settings, "consultops_contacts_api_url", "https://consultops.mateoconsultinginc.com/api/integrations/contacts"),
        patch.object(public_router.settings, "integration_api_key", ""),
    ):
        response = client.post(
            "/api/contact",
            data={
                "name": "Test User",
                "email": "test@example.com",
                "message": "Hello",
                "captcha_a": 2,
                "captcha_b": 3,
                "captcha_answer": "5",
            },
        )
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_contact_config_health_reports_not_ready_without_api_key():
    import app.routers.public as public_router

    with (
        patch.object(
            public_router.settings,
            "consultops_contacts_api_url",
            "https://consultops.mateoconsultinginc.com/api/integrations/contacts",
        ),
        patch.object(public_router.settings, "integration_api_key", ""),
    ):
        response = client.get("/health/contact-config")

    assert response.status_code == 200
    body = response.json()
    assert body["contact_form_ready"] is False
    assert body["has_contacts_api_url"] is True
    assert body["has_integration_api_key"] is False


def test_contact_config_health_reports_ready_when_fully_configured():
    import app.routers.public as public_router

    with (
        patch.object(
            public_router.settings,
            "consultops_contacts_api_url",
            "https://consultops.mateoconsultinginc.com/api/integrations/contacts",
        ),
        patch.object(public_router.settings, "integration_api_key", "test-key"),
    ):
        response = client.get("/health/contact-config")

    assert response.status_code == 200
    body = response.json()
    assert body["contact_form_ready"] is True
    assert body["has_contacts_api_url"] is True
    assert body["has_integration_api_key"] is True


def test_contact_api_proxies_to_consultops_on_success():
    import app.routers.public as public_router

    mock_response = MagicMock()
    mock_response.status_code = 201

    mock_http_client = AsyncMock()
    mock_http_client.post = AsyncMock(return_value=mock_response)
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=None)

    with (
        patch.object(
            public_router.settings,
            "consultops_contacts_api_url",
            "https://consultops.mateoconsultinginc.com/api/integrations/contacts",
        ),
        patch.object(public_router.settings, "integration_api_key", "test-key"),
        patch("app.routers.public.httpx.AsyncClient", return_value=mock_http_client),
    ):
        response = client.post(
            "/api/contact",
            data={
                "name": "Jane Doe",
                "email": "jane@example.com",
                "message": "Need customization",
                "captcha_a": 4,
                "captcha_b": 5,
                "captcha_answer": "9",
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert "sent successfully" in body["message"]

    mock_http_client.post.assert_awaited_once()
    call_kwargs = mock_http_client.post.await_args.kwargs
    assert call_kwargs["json"]["name"] == "Jane Doe"
    assert call_kwargs["json"]["email"] == "jane@example.com"
    assert call_kwargs["json"]["notes"] == "Need customization"
    assert call_kwargs["headers"]["X-API-Key"] == "test-key"
    assert call_kwargs["headers"]["Content-Type"] == "application/json"
    assert (
        str(mock_http_client.post.await_args.args[0])
        == "https://consultops.mateoconsultinginc.com/api/integrations/contacts"
    )
