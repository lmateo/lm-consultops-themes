from fastapi.testclient import TestClient

from app.main import app
from app.services.preview_demos import SLUG_LAYOUT_MAP, get_layout_key

client = TestClient(app)

ALL_SLUGS = list(SLUG_LAYOUT_MAP.keys())
DEMO_PAGES = ["", "/about", "/services", "/contact"]


def test_each_template_has_unique_layout_key():
    layouts = {get_layout_key(slug) for slug in ALL_SLUGS}
    assert len(layouts) == len(ALL_SLUGS)


def test_preview_site_home_returns_200_for_all_templates():
    for slug in ALL_SLUGS:
        response = client.get(f"/preview-site/{slug}")
        assert response.status_code == 200, slug
        assert template_unique_marker(slug) in response.text


def test_preview_site_inner_pages_active():
    slug = "cloudcare-it"
    for suffix in ["/about", "/services", "/contact"]:
        response = client.get(f"/preview-site/{slug}{suffix}")
        assert response.status_code == 200
        assert "demo-page-section" in response.text


def test_about_page_includes_rich_team_and_timeline():
    response = client.get("/preview-site/greenfield-farm/about")
    assert response.status_code == 200
    assert "Mara Ashford" in response.text
    assert "Milestones" in response.text
    assert "timeline" in response.text


def test_services_page_includes_offerings_and_pricing():
    response = client.get("/preview-site/pizza-local-eats/services")
    assert response.status_code == 200
    assert "Catering Trays" in response.text
    assert "offering-card" in response.text


def test_contact_page_includes_form_and_faqs():
    response = client.get("/preview-site/mountain-lodge/contact")
    assert response.status_code == 200
    assert "Timberline Road" in response.text
    assert "faq-item" in response.text
    assert "Submit inquiry" in response.text


def test_different_templates_render_different_layout_markers():
    agrarian = client.get("/preview-site/greenfield-farm").text
    saas = client.get("/preview-site/cloudcare-it").text
    assert "Agrarian" in agrarian or "produce-card" in agrarian
    assert "Managed IT Console" in saas or "feature-matrix" in saas
    assert agrarian != saas


def template_unique_marker(slug: str) -> str:
    markers = {
        "greenfield-farm": "produce-card",
        "tradepro-local": "trade-card",
        "pizza-local-eats": "menu-item",
        "cloudcare-it": "feature-matrix",
        "mountain-lodge": "room-card",
        "petcare-studio": "appt-card",
        "community-impact": "impact-band",
        "homebase-realty": "listing",
        "autoworks-garage": "pricing-table",
        "wellness-local": "pathway",
    }
    return markers.get(slug, "demo-nav")
