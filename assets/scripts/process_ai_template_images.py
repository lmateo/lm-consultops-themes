from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

SLUGS = [
    "greenfield-farm",
    "tradepro-local",
    "pizza-local-eats",
    "cloudcare-it",
    "mountain-lodge",
    "petcare-studio",
    "community-impact",
    "homebase-realty",
    "autoworks-garage",
    "wellness-local",
]

SOURCE_DIR = Path("assets/ai-sources")
FALLBACK_SOURCE_DIRS = (Path("."), Path("assets"))
OUTPUT_ROOT = Path("app/static/images/templates")

CROPS = {
    "hero": (1600, 900, (0.0, 0.05, 1.0, 0.88)),
    "hero-mobile": (900, 1200, (0.12, 0.0, 0.88, 1.0)),
    "thumbnail": (800, 480, (0.0, 0.1, 1.0, 0.82)),
    "preview": (1440, 900, (0.02, 0.04, 0.98, 0.9)),
    "about": (1280, 720, (0.05, 0.08, 0.92, 0.94)),
    "services": (1280, 720, (0.0, 0.02, 0.95, 0.88)),
    "contact": (1280, 720, (0.03, 0.12, 0.97, 0.98)),
    "gallery-1": (1280, 720, (0.0, 0.02, 0.95, 0.88)),
    "gallery-2": (1280, 720, (0.06, 0.05, 1.0, 0.92)),
    "gallery-3": (1280, 720, (0.03, 0.12, 0.97, 0.98)),
}


def load_source(slug: str) -> Image.Image:
    filename = f"{slug}-ai.png"
    candidates = [SOURCE_DIR / filename, *[base / filename for base in FALLBACK_SOURCE_DIRS]]
    path = next((candidate for candidate in candidates if candidate.exists()), None)
    if path is None:
        checked = ", ".join(str(candidate) for candidate in candidates)
        raise FileNotFoundError(f"Missing AI source image for {slug}; checked: {checked}")
    image = Image.open(path)
    if image.mode != "RGB":
        image = image.convert("RGB")
    return image


def export_variant(src: Image.Image, out_path: Path, size: tuple[int, int], crop_box: tuple[float, float, float, float]):
    w, h = src.size
    focus = src.crop((int(w * crop_box[0]), int(h * crop_box[1]), int(w * crop_box[2]), int(h * crop_box[3])))
    # Keep the full framed focus visible by fitting inside target dimensions.
    fitted = ImageOps.contain(focus, size, Image.Resampling.LANCZOS)
    image = Image.new("RGB", size, (248, 250, 252))
    offset = ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2)
    image.paste(fitted, offset)
    image = ImageEnhance.Sharpness(image).enhance(1.06)
    image = ImageEnhance.Color(image).enhance(1.03)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path, "WEBP", quality=86, method=6)


def process_slug(slug: str):
    src = load_source(slug)
    target = OUTPUT_ROOT / slug
    for name, (width, height, crop) in CROPS.items():
        filename = f"{name}.webp" if not name.startswith("gallery") else f"{name}.webp"
        export_variant(src, target / filename, (width, height), crop)
    print(f"Processed {slug}")


def main():
    for slug in SLUGS:
        process_slug(slug)
    print(f"Exported AI-based WebP sets to {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
