import re

from fastapi.testclient import TestClient

from app.main import app
from app.services.crafto_preview_wrap import (
    _preview_image_pool,
    _resolve_preview_href,
    rewrite_crafto_preview_links,
)
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
    assert "/static/css/preview-chrome.css" in response.text


def test_wrapped_preview_nav_links_use_mateo_routes():
    response = client.get("/preview/cloudcare-it/home")
    assert response.status_code == 200
    text = response.text
    assert 'href="/preview/cloudcare-it/home"' in text
    assert 'href="/preview/cloudcare-it/about"' in text
    assert 'href="/preview/cloudcare-it/services"' in text
    assert 'href="/preview/cloudcare-it/contact"' in text
    assert 'href="demo-it-business.html"' not in text
    assert 'href="index.html"' not in text
    assert "themezaa.com" not in text


def test_wrapped_preview_unmapped_demo_pages_use_hash():
    response = client.get("/preview/cloudcare-it/home")
    assert response.status_code == 200
    assert 'href="demo-it-business-blog.html"' not in response.text
    assert 'href="#"' in response.text


def test_resolve_preview_href_maps_crafto_vendor_urls():
    crafto = get_crafto_demo_or_default("cloudcare-it")
    assert _resolve_preview_href("https://www.themezaa.com/", slug="cloudcare-it", crafto=crafto) == "#"
    assert (
        _resolve_preview_href("demo-it-business-about.html", slug="cloudcare-it", crafto=crafto)
        == "/preview/cloudcare-it/about"
    )


def test_rewrite_crafto_preview_links_unit():
    crafto = get_crafto_demo_or_default("cloudcare-it")
    html = '<a href="demo-it-business-contact.html">Contact</a>'
    assert (
        rewrite_crafto_preview_links(html, slug="cloudcare-it", crafto=crafto)
        == '<a href="/preview/cloudcare-it/contact">Contact</a>'
    )


def test_wrapped_preview_uses_template_photos_not_placeholders():
    response = client.get("/preview/greenfield-farm/home")
    assert response.status_code == 200
    assert "placehold.co" not in response.text
    assert "/static/images/templates/greenfield-farm/hero.webp" in response.text


def test_wrapped_preview_uses_varied_template_images():
    response = client.get("/preview/greenfield-farm/home")
    assert response.status_code == 200
    images = re.findall(r"/static/images/templates/greenfield-farm/([\w-]+\.webp)", response.text)
    assert len(set(images)) >= 8


def test_template_image_discovery_includes_extended_gallery_set():
    pool = _preview_image_pool("services", "pizza-local-eats")
    assert "gallery-8.webp" in pool
    assert "team.webp" in pool or "feature.webp" in pool
    assert len(pool) >= 12


def test_image_pool_applies_page_primary_and_slug_weighting():
    home_pool = _preview_image_pool("home", "pizza-local-eats")
    services_pool = _preview_image_pool("services", "cloudcare-it")
    contact_pool = _preview_image_pool("contact", "community-impact")

    assert home_pool[0] == "hero.webp"
    assert services_pool[0] == "services.webp"
    assert contact_pool[0] == "contact.webp"

    assert home_pool.count("gallery-1.webp") > 1
    assert services_pool.count("services.webp") > 1


def test_wrapped_preview_inner_pages_use_page_banners():
    response = client.get("/preview/cloudcare-it/about")
    assert response.status_code == 200
    assert "placehold.co" not in response.text
    assert "/static/images/templates/cloudcare-it/about.webp" in response.text

    response = client.get("/preview/cloudcare-it/services")
    assert response.status_code == 200
    assert "/static/images/templates/cloudcare-it/services.webp" in response.text

    response = client.get("/preview/cloudcare-it/contact")
    assert response.status_code == 200
    assert "/static/images/templates/cloudcare-it/contact.webp" in response.text


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
