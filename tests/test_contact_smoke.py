"""Smoke tests for contact form page and /api/contact endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_contact_page_loads_with_turnstile():
    import app.routers.public as public_router

    with (
        patch.object(public_router.settings, "turnstile_site_key", "test-site-key"),
        patch.object(public_router.settings, "turnstile_secret_key", "test-secret-key"),
    ):
        response = client.get("/contact")

    assert response.status_code == 200
    html = response.text
    assert "Customization Request" in html
    assert 'action="/api/contact"' in html
    assert 'name="website"' in html
    assert 'class="cf-turnstile"' in html
    assert 'data-sitekey="test-site-key"' in html
    assert "challenges.cloudflare.com/turnstile/v0/api.js" in html


def test_contact_page_omits_turnstile_when_not_configured():
    import app.routers.public as public_router

    with (
        patch.object(public_router.settings, "turnstile_site_key", ""),
        patch.object(public_router.settings, "turnstile_secret_key", ""),
    ):
        response = client.get("/contact")

    assert response.status_code == 200
    html = response.text
    assert 'class="cf-turnstile"' not in html
    assert "challenges.cloudflare.com/turnstile/v0/api.js" not in html


def test_contact_api_rejects_honeypot():
    import app.routers.public as public_router

    with (
        patch.object(public_router.settings, "turnstile_site_key", "test-site-key"),
        patch.object(public_router.settings, "turnstile_secret_key", "test-secret-key"),
        patch("app.routers.public.verify_turnstile_token", new=AsyncMock(return_value=True)),
    ):
        response = client.post(
            "/api/contact",
            data={
                "name": "Test User",
                "email": "test@example.com",
                "message": "Hello",
                "website": "https://spam.example",
                "cf-turnstile-response": "valid-token",
            },
        )
    assert response.status_code == 400
    assert "Invalid submission" in response.json()["detail"]


def test_contact_api_rejects_invalid_turnstile():
    import app.routers.public as public_router

    with (
        patch.object(public_router.settings, "turnstile_site_key", "test-site-key"),
        patch.object(public_router.settings, "turnstile_secret_key", "test-secret-key"),
        patch("app.routers.public.verify_turnstile_token", new=AsyncMock(return_value=False)),
    ):
        response = client.post(
            "/api/contact",
            data={
                "name": "Test User",
                "email": "test@example.com",
                "message": "Hello",
                "cf-turnstile-response": "invalid-token",
            },
        )
    assert response.status_code == 400
    assert "Security verification failed" in response.json()["detail"]


def test_contact_api_returns_503_when_not_configured():
    import app.routers.public as public_router

    with (
        patch.object(public_router.settings, "consultops_contacts_api_url", "https://consultops.mateoconsultinginc.com/api/integrations/contacts"),
        patch.object(public_router.settings, "integration_api_key", ""),
        patch.object(public_router.settings, "turnstile_site_key", "test-site-key"),
        patch.object(public_router.settings, "turnstile_secret_key", "test-secret-key"),
        patch("app.routers.public.verify_turnstile_token", new=AsyncMock(return_value=True)),
    ):
        response = client.post(
            "/api/contact",
            data={
                "name": "Test User",
                "email": "test@example.com",
                "message": "Hello",
                "cf-turnstile-response": "valid-token",
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
        patch.object(public_router.settings, "turnstile_site_key", "test-site-key"),
        patch.object(public_router.settings, "turnstile_secret_key", "test-secret-key"),
    ):
        response = client.get("/health/contact-config")

    assert response.status_code == 200
    body = response.json()
    assert body["contact_form_ready"] is False
    assert body["has_contacts_api_url"] is True
    assert body["has_integration_api_key"] is False
    assert body["has_turnstile"] is True


def test_contact_config_health_reports_ready_when_fully_configured():
    import app.routers.public as public_router

    with (
        patch.object(
            public_router.settings,
            "consultops_contacts_api_url",
            "https://consultops.mateoconsultinginc.com/api/integrations/contacts",
        ),
        patch.object(public_router.settings, "integration_api_key", "test-key"),
        patch.object(public_router.settings, "turnstile_site_key", "test-site-key"),
        patch.object(public_router.settings, "turnstile_secret_key", "test-secret-key"),
    ):
        response = client.get("/health/contact-config")

    assert response.status_code == 200
    body = response.json()
    assert body["contact_form_ready"] is True
    assert body["has_contacts_api_url"] is True
    assert body["has_integration_api_key"] is True
    assert body["has_turnstile"] is True


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
        patch.object(public_router.settings, "turnstile_site_key", "test-site-key"),
        patch.object(public_router.settings, "turnstile_secret_key", "test-secret-key"),
        patch("app.routers.public.verify_turnstile_token", new=AsyncMock(return_value=True)),
        patch("app.routers.public.httpx.AsyncClient", return_value=mock_http_client),
    ):
        response = client.post(
            "/api/contact",
            data={
                "name": "Jane Doe",
                "email": "jane@example.com",
                "message": "Need customization",
                "cf-turnstile-response": "valid-token",
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
