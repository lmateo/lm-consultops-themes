from fastapi.testclient import TestClient

from app.main import app
from app.services.crafto_demos import CRAFTO_TEMPLATE_DEMOS, get_crafto_demo_or_default
from app.services.preview_demos import SLUG_LAYOUT_MAP, get_layout_key

client = TestClient(app)

ALL_SLUGS = list(SLUG_LAYOUT_MAP.keys())
CRAFTO_PAGES = ["", "/about", "/services", "/contact"]


def test_each_template_has_unique_layout_key():
    layouts = {get_layout_key(slug) for slug in ALL_SLUGS}
    assert len(layouts) == len(ALL_SLUGS)


def test_preview_site_redirects_to_crafto_for_all_templates():
    for slug in ALL_SLUGS:
        mapping = get_crafto_demo_or_default(slug)
        response = client.get(f"/preview-site/{slug}", follow_redirects=False)
        assert response.status_code == 302, slug
        assert response.headers["location"] == mapping.page_path("home")


def test_preview_site_inner_pages_redirect_to_crafto():
    slug = "cloudcare-it"
    mapping = get_crafto_demo_or_default(slug)
    for page, suffix in [
        ("about", "/about"),
        ("services", "/services"),
        ("contact", "/contact"),
    ]:
        response = client.get(f"/preview-site/{slug}{suffix}", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == mapping.page_path(page)


def test_crafto_static_home_demo_renders():
    mapping = get_crafto_demo_or_default("greenfield-farm")
    response = client.get(mapping.page_path("home"))
    assert response.status_code == 200
    assert "demo-green-energy" in response.text or "green-energy" in response.text


def test_crafto_pizza_menu_page_renders():
    mapping = get_crafto_demo_or_default("pizza-local-eats")
    response = client.get(mapping.page_path("services"))
    assert response.status_code == 200
    assert "pizza-parlor" in response.text


def test_crafto_mappings_cover_all_marketplace_slugs():
    assert set(CRAFTO_TEMPLATE_DEMOS.keys()) == set(ALL_SLUGS)


def test_live_preview_page_lists_crafto_demo():
    response = client.get("/preview/cloudcare-it")
    assert response.status_code == 200
    assert "IT Business" in response.text
    assert "demo-it-business.html" in response.text
