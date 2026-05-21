from pathlib import Path

from app.services.preview_demos import SLUG_LAYOUT_MAP

ROOT = Path("app/static/images/templates")
REQUIRED = (
    "hero.webp",
    "hero-mobile.webp",
    "thumbnail.webp",
    "preview.webp",
    "about.webp",
    "services.webp",
    "contact.webp",
    "gallery-1.webp",
    "gallery-2.webp",
    "gallery-3.webp",
)


def test_each_template_has_page_specific_images():
    for slug in SLUG_LAYOUT_MAP:
        folder = ROOT / slug
        assert folder.is_dir(), slug
        for name in REQUIRED:
            path = folder / name
            assert path.is_file(), f"{slug}/{name}"
            assert path.stat().st_size > 2_000, f"{slug}/{name} too small"


def test_gallery_images_differ_per_template():
    """Gallery files should not be byte-identical across page roles."""
    slug = "greenfield-farm"
    g1 = (ROOT / slug / "gallery-1.webp").read_bytes()
    g2 = (ROOT / slug / "gallery-2.webp").read_bytes()
    g3 = (ROOT / slug / "gallery-3.webp").read_bytes()
    assert g1 != g2 != g3
