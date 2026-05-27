"""Smoke test for contact API proxy wiring."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_contact_form_posts_to_configured_contacts_api():
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
        patch.object(public_router.settings, "integration_api_key", "smoke-test-key"),
        patch("app.routers.public.httpx.AsyncClient", return_value=mock_http_client),
    ):
        response = client.post(
            "/api/contact",
            data={
                "name": "Smoke Tester",
                "email": "smoke@example.com",
                "message": "Contact wiring smoke test",
                "captcha_a": 3,
                "captcha_b": 4,
                "captcha_answer": "7",
            },
        )

    assert response.status_code == 201
    mock_http_client.post.assert_awaited_once()
    call_args = mock_http_client.post.await_args
    assert str(call_args.args[0]) == "https://consultops.mateoconsultinginc.com/api/integrations/contacts"
    assert call_args.kwargs["json"] == {
        "name": "Smoke Tester",
        "email": "smoke@example.com",
        "notes": "Contact wiring smoke test",
    }
