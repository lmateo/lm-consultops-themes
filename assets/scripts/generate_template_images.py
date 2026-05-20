from __future__ import annotations

import math
import random
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


@dataclass(frozen=True)
class TemplateTheme:
    slug: str
    colors: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]
    motifs: tuple[str, ...]


THEMES: list[TemplateTheme] = [
    TemplateTheme("greenfield-farm", ((32, 96, 58), (156, 198, 102), (227, 243, 210)), ("hill", "barn", "tree", "sun")),
    TemplateTheme(
        "tradepro-local",
        ((34, 56, 89), (237, 126, 49), (210, 223, 238)),
        ("grid", "building", "panel", "line"),
    ),
    TemplateTheme(
        "pizza-local-eats",
        ((131, 39, 23), (223, 126, 56), (250, 234, 202)),
        ("circle", "table", "lamp", "steam"),
    ),
    TemplateTheme(
        "cloudcare-it",
        ((19, 55, 90), (49, 142, 201), (201, 229, 247)),
        ("cloud", "screen", "line", "pulse"),
    ),
    TemplateTheme(
        "mountain-lodge",
        ((41, 71, 106), (127, 170, 216), (226, 236, 246)),
        ("mountain", "cabin", "pine", "sun"),
    ),
    TemplateTheme(
        "petcare-studio",
        ((39, 123, 118), (138, 194, 172), (236, 246, 241)),
        ("paw", "arc", "dot", "heart"),
    ),
    TemplateTheme(
        "community-impact",
        ((42, 109, 86), (95, 167, 130), (226, 241, 227)),
        ("people", "bubble", "leaf", "line"),
    ),
    TemplateTheme(
        "homebase-realty",
        ((58, 75, 84), (158, 124, 90), (234, 224, 212)),
        ("roof", "window", "line", "tree"),
    ),
    TemplateTheme(
        "autoworks-garage",
        ((33, 39, 48), (189, 57, 45), (209, 216, 224)),
        ("car", "gear", "stripe", "bolt"),
    ),
    TemplateTheme(
        "wellness-local",
        ((78, 112, 118), (145, 182, 170), (231, 241, 238)),
        ("leaf", "wave", "circle", "line"),
    ),
]

OUTPUT_ROOT = Path("app/static/images/templates")


def vertical_gradient(size: tuple[int, int], top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    width, height = size
    gradient = Image.new("RGB", size)
    draw = ImageDraw.Draw(gradient)
    for y in range(height):
        blend = y / max(height - 1, 1)
        color = tuple(int(top[i] * (1 - blend) + bottom[i] * blend) for i in range(3))
        draw.line([(0, y), (width, y)], fill=color)
    return gradient


def draw_motif(draw: ImageDraw.ImageDraw, motif: str, bounds: tuple[int, int, int, int], color: tuple[int, int, int], width: int):
    x0, y0, x1, y1 = bounds
    if motif in {"circle", "sun", "dot"}:
        draw.ellipse(bounds, outline=color, width=width)
    elif motif in {"line", "wave", "stripe"}:
        mid = (y0 + y1) // 2
        points = []
        segments = 6
        step = max((x1 - x0) // segments, 1)
        amp = max((y1 - y0) // 4, 1)
        for i in range(segments + 1):
            x = x0 + i * step
            y = mid + int(math.sin(i * 0.85) * amp)
            points.append((x, y))
        draw.line(points, fill=color, width=width)
    elif motif in {"grid", "window", "panel"}:
        draw.rectangle(bounds, outline=color, width=width)
        for gx in range(x0 + 20, x1, 35):
            draw.line([(gx, y0), (gx, y1)], fill=color, width=1)
        for gy in range(y0 + 20, y1, 35):
            draw.line([(x0, gy), (x1, gy)], fill=color, width=1)
    elif motif in {"mountain", "roof", "barn", "cabin"}:
        draw.polygon([(x0, y1), ((x0 + x1) // 2, y0), (x1, y1)], outline=color, fill=None, width=width)
        draw.rectangle([x0 + 22, y1 - 44, x1 - 22, y1], outline=color, width=width)
    elif motif in {"tree", "pine", "leaf"}:
        draw.polygon([((x0 + x1) // 2, y0), (x0, y1), (x1, y1)], outline=color, fill=None, width=width)
        trunk_x = (x0 + x1) // 2
        draw.line([(trunk_x, y1), (trunk_x, y1 + 20)], fill=color, width=width)
    elif motif in {"cloud", "steam", "bubble"}:
        draw.ellipse([x0, y0 + 12, x0 + (x1 - x0) // 2, y1], outline=color, width=width)
        draw.ellipse([x0 + 24, y0, x1, y1 - 10], outline=color, width=width)
    elif motif in {"people", "heart", "paw", "gear", "car", "bolt", "building", "pulse", "table", "arc"}:
        # Fallback rounded geometry with accent lines.
        draw.rounded_rectangle(bounds, radius=14, outline=color, width=width)
        draw.line([(x0 + 10, y1 - 12), (x1 - 10, y0 + 12)], fill=color, width=max(width - 1, 1))
    else:
        draw.rectangle(bounds, outline=color, width=width)


def create_base(theme: TemplateTheme, size: tuple[int, int] = (1920, 1200)) -> Image.Image:
    random.seed(theme.slug)
    base = vertical_gradient(size, theme.colors[0], theme.colors[1])
    overlay = vertical_gradient(size, theme.colors[1], theme.colors[2])
    overlay = ImageEnhance.Brightness(overlay).enhance(1.1)
    base = Image.blend(base, overlay, 0.35)
    draw = ImageDraw.Draw(base)

    width, height = size
    accent = tuple(max(c - 25, 0) for c in theme.colors[0])
    light = tuple(min(c + 20, 255) for c in theme.colors[2])

    for i in range(22):
        box_w = random.randint(120, 320)
        box_h = random.randint(90, 240)
        x0 = random.randint(-40, width - 90)
        y0 = random.randint(-30, height - 90)
        x1 = min(x0 + box_w, width + 40)
        y1 = min(y0 + box_h, height + 40)
        motif = theme.motifs[i % len(theme.motifs)]
        color = accent if i % 2 == 0 else light
        draw_motif(draw, motif, (x0, y0, x1, y1), color=color, width=3)

    # Soft vignette for premium depth.
    vignette = Image.new("RGBA", size, (0, 0, 0, 0))
    vdraw = ImageDraw.Draw(vignette)
    for r in range(max(width, height), 0, -90):
        alpha = int((1 - (r / max(width, height))) * 70)
        vdraw.ellipse(
            [width // 2 - r, height // 2 - r, width // 2 + r, height // 2 + r],
            outline=(0, 0, 0, alpha),
            width=35,
        )
    base = Image.alpha_composite(base.convert("RGBA"), vignette).convert("RGB")
    return base.filter(ImageFilter.GaussianBlur(radius=0.15))


def export_variant(src: Image.Image, out_path: Path, size: tuple[int, int], crop_box: tuple[float, float, float, float], sharpen: float = 1.0):
    w, h = src.size
    crop = src.crop((int(w * crop_box[0]), int(h * crop_box[1]), int(w * crop_box[2]), int(h * crop_box[3])))
    image = crop.resize(size, Image.Resampling.LANCZOS)
    if sharpen > 1.0:
        image = ImageEnhance.Sharpness(image).enhance(sharpen)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path, "WEBP", quality=88, method=6)


def generate_template_assets(theme: TemplateTheme):
    base = create_base(theme)
    target = OUTPUT_ROOT / theme.slug
    target.mkdir(parents=True, exist_ok=True)

    export_variant(base, target / "hero.webp", (1600, 900), (0.0, 0.05, 1.0, 0.8), sharpen=1.1)
    export_variant(base, target / "hero-mobile.webp", (900, 1200), (0.18, 0.0, 0.82, 1.0), sharpen=1.15)
    export_variant(base, target / "thumbnail.webp", (800, 480), (0.0, 0.12, 1.0, 0.78), sharpen=1.2)
    export_variant(base, target / "preview.webp", (1440, 900), (0.02, 0.02, 0.98, 0.87), sharpen=1.15)
    export_variant(base, target / "gallery-1.webp", (1280, 720), (0.0, 0.0, 0.92, 0.86), sharpen=1.1)
    export_variant(base, target / "gallery-2.webp", (1280, 720), (0.08, 0.05, 1.0, 0.92), sharpen=1.05)
    export_variant(base, target / "gallery-3.webp", (1280, 720), (0.04, 0.14, 0.96, 0.98), sharpen=1.12)


def main():
    for theme in THEMES:
        generate_template_assets(theme)
    print(f"Generated assets for {len(THEMES)} templates in {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
