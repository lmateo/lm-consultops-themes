from fastapi.testclient import TestClient

from app.main import app
from app.services.preview_demos import SLUG_LAYOUT_MAP, list_template_search_hints

client = TestClient(app)


def test_search_hints_cover_all_demo_templates():
    assert {h["slug"] for h in list_template_search_hints()} == set(SLUG_LAYOUT_MAP.keys())


def test_homepage_has_no_themeforest_links():
    response = client.get("/")
    assert response.status_code == 200
    assert "themeforest.net" not in response.text.lower()
    assert "Layout reference previews" not in response.text


def test_template_detail_has_no_layout_reference_links():
    response = client.get("/templates/greenfield-farm")
    assert response.status_code == 200
    assert "themeforest.net" not in response.text.lower()
    assert "Layout references" not in response.text


def test_preview_home_uses_full_page_crafto_chrome():
    response = client.get("/preview-site/cloudcare-it", follow_redirects=True)
    assert response.status_code == 200
    assert "mkt-preview-chrome" in response.text
    assert "preview-chrome.css" in response.text
    assert "<iframe" not in response.text.lower()
