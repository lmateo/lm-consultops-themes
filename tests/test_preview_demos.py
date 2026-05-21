import re

from fastapi.testclient import TestClient

from app.main import app
from app.services.crafto_demos import CRAFTO_TEMPLATE_DEMOS, get_crafto_demo_or_default
from app.services.preview_demos import SLUG_LAYOUT_MAP, get_layout_key

client = TestClient(app)

ALL_SLUGS = list(SLUG_LAYOUT_MAP.keys())


def test_each_template_has_unique_layout_key():
    layouts = {get_layout_key(slug) for slug in ALL_SLUGS}
    assert len(layouts) == len(ALL_SLUGS)


def test_preview_root_redirects_to_wrapped_home():
    response = client.get("/preview/cloudcare-it", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/preview/cloudcare-it/home"


def test_preview_site_redirects_to_wrapped_preview():
    for slug in ALL_SLUGS:
        response = client.get(f"/preview-site/{slug}", follow_redirects=False)
        assert response.status_code == 302, slug
        assert response.headers["location"] == f"/preview/{slug}/home"


def test_preview_site_inner_pages_redirect_to_wrapped_preview():
    slug = "cloudcare-it"
    for page, suffix in [
        ("about", "/about"),
        ("services", "/services"),
        ("contact", "/contact"),
    ]:
        response = client.get(f"/preview-site/{slug}{suffix}", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == f"/preview/{slug}/{page}"


def test_wrapped_preview_renders_without_iframe():
    response = client.get("/preview/cloudcare-it/home")
    assert response.status_code == 200
    assert "mkt-preview-chrome" in response.text
    assert "<iframe" not in response.text.lower()
    assert 'base href="/crafto/"' in response.text
    assert 'id="mkt-preview-viewport"' in response.text
    assert 'id="mkt-preview-canvas"' in response.text
    assert "/static/css/preview-mobile.css" in response.text


def test_wrapped_preview_uses_template_photos_not_placeholders():
    response = client.get("/preview/greenfield-farm/home")
    assert response.status_code == 200
    assert "placehold.co" not in response.text
    assert "/static/images/templates/greenfield-farm/hero.webp" in response.text


def test_wrapped_preview_uses_varied_template_images():
    response = client.get("/preview/greenfield-farm/home")
    assert response.status_code == 200
    images = re.findall(r"/static/images/templates/greenfield-farm/([\w-]+\.webp)", response.text)
    assert len(set(images)) >= 4


def test_wrapped_preview_inner_pages_use_page_banners():
    response = client.get("/preview/cloudcare-it/about")
    assert response.status_code == 200
    assert "placehold.co" not in response.text
    assert "/static/images/templates/cloudcare-it/about.webp" in response.text


def test_wrapped_preview_includes_crafto_assets():
    response = client.get("/preview/greenfield-farm/home")
    assert response.status_code == 200
    assert "green-energy" in response.text or "demo-green-energy" in response.text


def test_crafto_static_home_demo_renders():
    mapping = get_crafto_demo_or_default("greenfield-farm")
    response = client.get(mapping.page_path("home"))
    assert response.status_code == 200
    assert "demo-green-energy" in response.text or "green-energy" in response.text


def test_crafto_mappings_cover_all_marketplace_slugs():
    assert set(CRAFTO_TEMPLATE_DEMOS.keys()) == set(ALL_SLUGS)
