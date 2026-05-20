from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageEnhance

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
OUTPUT_ROOT = Path("app/static/images/templates")

CROPS = {
    "hero": (1600, 900, (0.0, 0.05, 1.0, 0.88)),
    "hero-mobile": (900, 1200, (0.12, 0.0, 0.88, 1.0)),
    "thumbnail": (800, 480, (0.0, 0.1, 1.0, 0.82)),
    "preview": (1440, 900, (0.02, 0.04, 0.98, 0.9)),
    "gallery-1": (1280, 720, (0.0, 0.02, 0.95, 0.88)),
    "gallery-2": (1280, 720, (0.06, 0.05, 1.0, 0.92)),
    "gallery-3": (1280, 720, (0.03, 0.12, 0.97, 0.98)),
}


def load_source(slug: str) -> Image.Image:
    path = SOURCE_DIR / f"{slug}-ai.png"
    if not path.exists():
        raise FileNotFoundError(f"Missing AI source image: {path}")
    image = Image.open(path)
    if image.mode != "RGB":
        image = image.convert("RGB")
    return image


def export_variant(src: Image.Image, out_path: Path, size: tuple[int, int], crop_box: tuple[float, float, float, float]):
    w, h = src.size
    crop = src.crop((int(w * crop_box[0]), int(h * crop_box[1]), int(w * crop_box[2]), int(h * crop_box[3])))
    image = crop.resize(size, Image.Resampling.LANCZOS)
    image = ImageEnhance.Sharpness(image).enhance(1.08)
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
