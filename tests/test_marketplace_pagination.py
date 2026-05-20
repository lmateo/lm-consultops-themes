from fastapi.testclient import TestClient

from app.main import app


def test_marketplace_pagination_with_empty_price_filters():
    client = TestClient(app)
    response = client.get("/marketplace?page=2&min_price=&max_price=&sort=newest")
    assert response.status_code == 200
    assert "min_price=" not in response.text or 'min_price=""' not in response.text


def test_marketplace_pagination_preserves_active_filters():
    client = TestClient(app)
    response = client.get("/marketplace?page=1&min_price=10&max_price=100&sort=price_low_high")
    assert response.status_code == 200
    assert "min_price=10" in response.text
    assert "max_price=100" in response.text
