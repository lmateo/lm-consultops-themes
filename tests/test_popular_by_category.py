from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_popular_by_category_page():
    response = client.get("/popular")
    assert response.status_code == 200
    assert "Explore templates by freshness and pricing." in response.text
    assert "mkt-list-row" in response.text
    assert "Live Preview" in response.text
    assert "Featured studios" in response.text


def test_popular_category_filter():
    response = client.get("/popular?category=technology&sort=top_rated")
    assert response.status_code == 200
    assert "Technology" in response.text
    assert "More featured" in response.text
    assert "mkt-pill" in response.text


def test_popular_bestselling_sort():
    response = client.get("/popular?sort=bestselling")
    assert response.status_code == 200
    assert "Featured" in response.text
    assert "Pre-launch" in response.text


def test_popular_pagination_with_empty_price_filters():
    response = client.get("/popular?page=2&min_price=&max_price=&sort=newest")
    assert response.status_code == 200


def test_popular_pagination_preserves_active_filters():
    response = client.get("/popular?page=1&min_price=10&max_price=100&sort=price_low_high")
    assert response.status_code == 200
    assert "min_price=10" in response.text
    assert "max_price=100" in response.text


def test_marketplace_redirects_to_popular():
    response = client.get("/marketplace?sort=bestselling&q=farm", follow_redirects=False)
    assert response.status_code == 301
    assert response.headers["location"] == "/popular?sort=bestselling&q=farm"


def test_category_page_sort_and_pagination():
    response = client.get("/categories/technology?sort=bestselling")
    assert response.status_code == 200
    assert "Technology Templates" in response.text
