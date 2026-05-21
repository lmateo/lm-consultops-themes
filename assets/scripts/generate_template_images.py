"""Generate royalty-free photorealistic procedural WebP imagery per template."""

from __future__ import annotations

import random
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

OUTPUT_ROOT = Path("app/static/images/templates")
SCENES = ("hero", "about", "services", "contact")
GALLERY_SCENE_COUNT = 12
INLINE_SCENE_NAMES = ("team", "blog", "feature", "showcase")
# Supersample heroes only; page/gallery frames export at target size for speed.
HERO_RENDER_SCALE = 1.25
PAGE_RENDER_SIZE = (1600, 1000)
GALLERY_RENDER_SIZE = (1440, 900)
WEBP_QUALITY = 92


@dataclass(frozen=True)
class TemplateTheme:
    slug: str
    label: str
    sky: tuple[int, int, int]
    mid: tuple[int, int, int]
    ground: tuple[int, int, int]
    accent: tuple[int, int, int]
    warmth: float
    painter: Callable[[str, tuple[int, int], random.Random, TemplateTheme], Image.Image]


@dataclass(frozen=True)
class SceneProfile:
    """Camera/lighting variation so each output frame feels like a distinct photograph."""

    composition_shift: float
    warmth_delta: float
    saturation: float
    contrast: float
    haze_strength: float
    sun_x_ratio: float
    sun_y_ratio: float
    sun_intensity: int
    bokeh_extra: int
    crop_focus: tuple[float, float, float, float]


def _rgb(r: int, g: int, b: int) -> tuple[int, int, int]:
    return (r, g, b)


def _shift(color: tuple[int, int, int], delta: int) -> tuple[int, int, int]:
    return tuple(max(0, min(255, c + delta)) for c in color)


def _seed(theme: TemplateTheme, scene: str) -> random.Random:
    return random.Random(f"{theme.slug}:{scene}")


def _build_scene_profile(scene: str, rng: random.Random, theme: TemplateTheme) -> SceneProfile:
    gallery_index = 0
    match = re.fullmatch(r"gallery-(\d+)", scene)
    if match:
        gallery_index = int(match.group(1))

    if scene == "hero":
        warmth_delta, contrast, haze = 0.08, 1.08, 0.06
        sun = (0.72 + rng.uniform(-0.06, 0.06), 0.18, 95)
        crop = (0.0, 0.02, 1.0, 0.92)
    elif scene == "about":
        warmth_delta, contrast, haze = 0.12, 1.04, 0.08
        sun = (0.62, 0.22, 80)
        crop = (0.04, 0.05, 0.96, 0.94)
    elif scene == "services":
        warmth_delta, contrast, haze = 0.04, 1.1, 0.05
        sun = (0.55, 0.2, 75)
        crop = (0.0, 0.03, 0.98, 0.9)
    elif scene == "contact":
        warmth_delta, contrast, haze = 0.06, 1.02, 0.1
        sun = (0.48, 0.24, 65)
        crop = (0.03, 0.08, 0.97, 0.98)
    elif scene in {"team", "blog", "feature", "showcase"}:
        warmth_delta, contrast, haze = 0.05, 1.06, 0.07
        sun = (0.58 + rng.uniform(-0.08, 0.08), 0.2, 70)
        crop = (0.05, 0.04, 0.95, 0.92)
    else:
        warmth_delta, contrast, haze = 0.03, 1.05, 0.07
        sun = (0.5 + rng.uniform(-0.2, 0.2), 0.2 + rng.uniform(-0.05, 0.05), 72)
        crop = (
            max(0.0, 0.02 * (gallery_index % 4)),
            max(0.0, 0.02 * ((gallery_index + 1) % 3)),
            min(1.0, 0.98 - 0.02 * (gallery_index % 3)),
            min(1.0, 0.96 - 0.02 * (gallery_index % 2)),
        )

    composition_shift = rng.uniform(-0.12, 0.12)
    if gallery_index:
        composition_shift = ((gallery_index % 7) - 3) * 0.035 + rng.uniform(-0.04, 0.04)

    return SceneProfile(
        composition_shift=composition_shift,
        warmth_delta=warmth_delta,
        saturation=1.05 + (gallery_index % 3) * 0.02,
        contrast=contrast,
        haze_strength=haze,
        sun_x_ratio=sun[0],
        sun_y_ratio=sun[1],
        sun_intensity=sun[2],
        bokeh_extra=4 + (gallery_index % 5),
        crop_focus=crop,
    )


def _lerp(a: int, b: int, t: float) -> int:
    return int(a * (1 - t) + b * t)


def _lerp_rgb(
    c0: tuple[int, int, int], c1: tuple[int, int, int], t: float
) -> tuple[int, int, int]:
    return (_lerp(c0[0], c1[0], t), _lerp(c0[1], c1[1], t), _lerp(c0[2], c1[2], t))


def vertical_gradient(
    size: tuple[int, int],
    stops: tuple[tuple[float, tuple[int, int, int]], ...],
) -> Image.Image:
    width, height = size
    img = Image.new("RGB", size)
    draw = ImageDraw.Draw(img)
    for y in range(height):
        t = y / max(height - 1, 1)
        for i in range(len(stops) - 1):
            p0, c0 = stops[i]
            p1, c1 = stops[i + 1]
            if p0 <= t <= p1:
                local = (t - p0) / max(p1 - p0, 1e-6)
                draw.line([(0, y), (width, y)], fill=_lerp_rgb(c0, c1, local))
                break
    return img


def _noise_layer(size: tuple[int, int], scale: float, opacity: int) -> Image.Image:
    w, h = size
    small = (max(64, w // 8), max(64, h // 8))
    noise = Image.effect_noise(small, 42).convert("L").resize(size, Image.Resampling.LANCZOS)
    return Image.merge("RGBA", [noise, noise, noise, Image.new("L", size, opacity)])


def _film_grain(size: tuple[int, int], rng: random.Random, opacity: int = 34) -> Image.Image:
    grain = Image.effect_noise((max(96, size[0] // 6), max(96, size[1] // 6)), rng.randint(35, 55))
    grain = grain.convert("L").resize(size, Image.Resampling.LANCZOS)
    return Image.merge("RGBA", [grain, grain, grain, Image.new("L", size, opacity)])


def _atmospheric_haze(size: tuple[int, int], strength: float) -> Image.Image:
    w, h = size
    haze = vertical_gradient(size, ((0.0, (245, 248, 252)), (0.55, (220, 228, 236)), (1.0, (180, 188, 198))))
    alpha = Image.new("L", size, int(255 * strength))
    return Image.merge("RGBA", [*haze.split(), alpha])


def _chromatic_aberration(img: Image.Image, amount: int = 2) -> Image.Image:
    if amount <= 0:
        return img
    red, green, blue = img.split()
    red = ImageChops.offset(red, -amount, 0)
    blue = ImageChops.offset(blue, amount, 0)
    return Image.merge("RGB", (red, green, blue))


def _highlight_bloom(img: Image.Image, intensity: float = 0.14) -> Image.Image:
    luminance = img.convert("L")
    bright = luminance.point(lambda value: 255 if value > 206 else 0)
    bright = bright.filter(ImageFilter.GaussianBlur(radius=14))
    warm = Image.new("RGB", img.size, (255, 244, 230))
    glow = Image.blend(img, warm, intensity)
    return Image.composite(glow, img, bright)


def _apply_scene_crop(img: Image.Image, crop: tuple[float, float, float, float]) -> Image.Image:
    w, h = img.size
    box = (int(w * crop[0]), int(h * crop[1]), int(w * crop[2]), int(h * crop[3]))
    cropped = img.crop(box)
    return cropped.resize((w, h), Image.Resampling.LANCZOS)


def _bokeh_layer(
    size: tuple[int, int], rng: random.Random, count: int, palette: tuple[tuple[int, int, int], ...]
) -> Image.Image:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    w, h = size
    for _ in range(count):
        r = rng.randint(18, 90)
        x = rng.randint(-r, w + r)
        y = rng.randint(0, h // 2)
        color = rng.choice(palette)
        alpha = rng.randint(18, 55)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(*color, alpha))
    return layer.filter(ImageFilter.GaussianBlur(radius=6))


def _rolling_hills(
    draw: ImageDraw.ImageDraw,
    w: int,
    h: int,
    y_ratio: float,
    color: tuple[int, int, int],
    rng: random.Random,
    *,
    amplitude: int = 36,
    steps: int = 14,
) -> None:
    y0 = int(h * y_ratio)
    points: list[tuple[int, int]] = [(0, h), (0, y0)]
    for i in range(1, steps):
        x = int(w * i / steps)
        y = y0 + rng.randint(-amplitude, amplitude)
        points.append((x, y))
    points.extend([(w, y0 + rng.randint(-12, 12)), (w, h)])
    draw.polygon(points, fill=color)


def _sun_glow(
    layer: Image.Image,
    center: tuple[int, int],
    radius: int,
    color: tuple[int, int, int],
    alpha: int,
) -> Image.Image:
    glow = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    cx, cy = center
    for r in range(radius, 0, -12):
        a = int(alpha * (r / radius) ** 1.6)
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(*color, a))
    return Image.alpha_composite(layer, glow.filter(ImageFilter.GaussianBlur(radius=8)))


def _figures(
    layer: Image.Image,
    positions: list[tuple[int, int, float]],
    color: tuple[int, int, int],
) -> Image.Image:
    sub = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(sub)
    for cx, base_y, scale in positions:
        w = int(34 * scale)
        h = int(96 * scale)
        head_r = int(14 * scale)
        draw.ellipse(
            (cx - head_r, base_y - h, cx + head_r, base_y - h + head_r * 2),
            fill=(*color, 220),
        )
        draw.rounded_rectangle(
            (cx - w, base_y - h + head_r * 2, cx + w, base_y),
            radius=10,
            fill=(*color, 220),
        )
    sub = sub.filter(ImageFilter.GaussianBlur(radius=1.6))
    return Image.alpha_composite(layer, sub)


def _paw(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    size: int,
    color: tuple[int, int, int],
    alpha: int = 220,
) -> None:
    cx, cy = center
    pad_r = max(8, size // 4)
    toe_r = max(4, size // 7)
    draw.ellipse((cx - pad_r, cy - pad_r, cx + pad_r, cy + pad_r), fill=(*color, alpha))
    offsets = [(-pad_r, -pad_r - toe_r), (0, -pad_r - toe_r - 4), (pad_r, -pad_r - toe_r), (-pad_r // 3, -pad_r - toe_r - 6)]
    for ox, oy in offsets:
        draw.ellipse((cx + ox - toe_r, cy + oy - toe_r, cx + ox + toe_r, cy + oy + toe_r), fill=(*color, alpha))


def _cross(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    size: int,
    color: tuple[int, int, int],
    alpha: int = 220,
) -> None:
    cx, cy = center
    arm = size // 2
    thick = max(8, size // 6)
    draw.rounded_rectangle((cx - thick // 2, cy - arm, cx + thick // 2, cy + arm), radius=4, fill=(*color, alpha))
    draw.rounded_rectangle((cx - arm, cy - thick // 2, cx + arm, cy + thick // 2), radius=4, fill=(*color, alpha))


def _heart(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    size: int,
    color: tuple[int, int, int],
    alpha: int = 210,
) -> None:
    cx, cy = center
    r = max(10, size // 4)
    draw.ellipse((cx - r - 8, cy - r, cx + 8, cy + r), fill=(*color, alpha))
    draw.ellipse((cx - 8, cy - r, cx + r + 8, cy + r), fill=(*color, alpha))
    draw.polygon([(cx - r - 10, cy), (cx + r + 10, cy), (cx, cy + size // 2 + 14)], fill=(*color, alpha))


def _photo_finish(
    img: Image.Image,
    theme: TemplateTheme,
    scene: str,
    profile: SceneProfile,
    rng: random.Random,
) -> Image.Image:
    is_hero = scene == "hero"
    img = ImageEnhance.Contrast(img).enhance(profile.contrast)
    img = ImageEnhance.Color(img).enhance(profile.saturation)
    img = ImageEnhance.Brightness(img).enhance(1.03 if scene in {"about", "contact"} else 1.0)
    if is_hero:
        img = _highlight_bloom(img, 0.16)
    elif scene.startswith("gallery-"):
        img = _highlight_bloom(img, 0.08)
    else:
        img = _highlight_bloom(img, 0.1)

    warmth = min(0.28, theme.warmth + profile.warmth_delta)
    if warmth > 0:
        warm = Image.new("RGB", img.size, (255, 224, 188))
        img = Image.blend(img, warm, warmth * (0.14 if scene != "contact" else 0.07))

    img = ImageOps.autocontrast(img, cutoff=1)
    if is_hero:
        blurred = img.filter(ImageFilter.GaussianBlur(radius=1.4))
        img = Image.blend(blurred, img, 0.84)
        img = ImageEnhance.Sharpness(img).enhance(1.14)
        img = _chromatic_aberration(img, amount=2)
    else:
        img = ImageEnhance.Sharpness(img).enhance(1.06)
        img = _chromatic_aberration(img, amount=1)

    grain_opacity = 30 if is_hero else 22
    img = Image.alpha_composite(img.convert("RGBA"), _film_grain(img.size, rng, grain_opacity)).convert("RGB")

    vignette = Image.new("L", img.size, 0)
    vdraw = ImageDraw.Draw(vignette)
    w, h = img.size
    vdraw.ellipse((-w // 5, -h // 7, w + w // 5, h + h // 3), fill=215)
    vignette = vignette.filter(ImageFilter.GaussianBlur(radius=max(8, min(w, h) // 6)))
    dark = Image.new("RGB", img.size, (10, 14, 20))
    return Image.composite(img, Image.composite(dark, img, vignette), vignette.point(lambda p: 255 - p))


def _compose(
    base: Image.Image,
    theme: TemplateTheme,
    scene: str,
    rng: random.Random,
    profile: SceneProfile,
    *,
    bokeh_palette: tuple[tuple[int, int, int], ...] | None = None,
    bokeh_count: int = 14,
) -> Image.Image:
    img = base.convert("RGBA")
    if profile.haze_strength > 0:
        img = Image.alpha_composite(img, _atmospheric_haze(img.size, profile.haze_strength))
    if bokeh_palette:
        total_bokeh = bokeh_count + profile.bokeh_extra
        img = Image.alpha_composite(img, _bokeh_layer(img.size, rng, total_bokeh, bokeh_palette))
    img = Image.alpha_composite(img, _noise_layer(img.size, 1.0, 18))
    finished = _photo_finish(img.convert("RGB"), theme, scene, profile, rng)
    return _apply_scene_crop(finished, profile.crop_focus)


def _finish_compose(
    img: Image.Image,
    theme: TemplateTheme,
    scene: str,
    rng: random.Random,
    *,
    bokeh_palette: tuple[tuple[int, int, int], ...] | None = None,
    bokeh_count: int = 14,
) -> Image.Image:
    profile = _build_scene_profile(scene, rng, theme)
    return _compose(
        img,
        theme,
        scene,
        rng,
        profile,
        bokeh_palette=bokeh_palette,
        bokeh_count=bokeh_count,
    )


# --- Industry painters (aligned with assets/prompts/*.txt) ---


def paint_greenfield_farm(
    scene: str, size: tuple[int, int], rng: random.Random, theme: TemplateTheme
) -> Image.Image:
    profile = _build_scene_profile(scene, rng, theme)
    w, h = size
    sky_top = _shift(theme.sky, 8)
    horizon = theme.mid
    base = vertical_gradient(
        size,
        ((0.0, sky_top), (0.42, horizon), (0.72, theme.ground), (1.0, _shift(theme.ground, -18))),
    )
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    _rolling_hills(draw, w, h, 0.56, _shift(theme.mid, -22), rng, amplitude=42)
    _rolling_hills(draw, w, h, 0.64, _shift(theme.ground, -8), rng, amplitude=28)
    fence_y = int(h * 0.62)
    for x in range(0, w, 46):
        draw.line([(x, fence_y), (x, fence_y - 44)], fill=(*_shift(theme.accent, 40), 180), width=3)
    draw.line([(0, fence_y), (w, fence_y)], fill=(*_shift(theme.accent, 55), 200), width=4)
    barn_w, barn_h = int(w * 0.22), int(h * 0.2)
    bx = int(w * ((0.58 if scene == "hero" else 0.42) + profile.composition_shift))
    by = int(h * 0.48)
    draw.polygon(
        [(bx, by), (bx + barn_w // 2, by - barn_h // 2), (bx + barn_w, by)],
        fill=(*_shift(theme.accent, -25), 230),
    )
    draw.rectangle((bx + 18, by, bx + barn_w - 18, by + barn_h), fill=(*_shift(theme.accent, 15), 240))
    for i in range(6):
        ox = 70 + i * 110
        draw.ellipse((ox, h - 180, ox + 26, h - 150), fill=(*_shift(theme.mid, 30), 160))
    img = Image.alpha_composite(base.convert("RGBA"), layer)
    img = _sun_glow(img, (int(w * 0.78), int(h * 0.16)), int(min(w, h) * 0.14), (255, 236, 190), 90)
    if scene == "about":
        img = _figures(img, [(w // 4, int(h * 0.72), 1.0), (w // 2, int(h * 0.7), 1.1), (3 * w // 4, int(h * 0.73), 0.95)], _shift(theme.accent, -40))
    return _finish_compose(
        img.convert("RGB"),
        theme,
        scene,
        rng,
        bokeh_palette=(theme.ground, theme.mid, (255, 240, 200)),
        bokeh_count=10,
    )


def paint_tradepro_local(
    scene: str, size: tuple[int, int], rng: random.Random, theme: TemplateTheme
) -> Image.Image:
    w, h = size
    base = vertical_gradient(size, ((0.0, theme.sky), (0.55, theme.mid), (1.0, theme.ground)))
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    house_x = int(w * 0.08)
    house_y = int(h * 0.38)
    hw, hh = int(w * 0.34), int(h * 0.28)
    draw.rectangle((house_x, house_y, house_x + hw, house_y + hh), fill=(*_shift(theme.ground, 25), 240))
    draw.polygon(
        [(house_x - 12, house_y), (house_x + hw // 2, house_y - hh // 3), (house_x + hw + 12, house_y)],
        fill=(*theme.accent, 220),
    )
    vx = int(w * 0.58)
    vy = int(h * 0.5)
    vw, vh = int(w * 0.3), int(h * 0.16)
    draw.rounded_rectangle((vx, vy, vx + vw, vy + vh), radius=12, fill=(*_shift(theme.sky, 35), 245))
    draw.rectangle((vx + 20, vy + 18, vx + vw - 20, vy + vh - 18), fill=(*theme.accent, 200))
    # Tool-inspired silhouette to better match contractor services.
    handle_y = int(h * 0.33)
    draw.rectangle((int(w * 0.18), handle_y, int(w * 0.36), handle_y + 18), fill=(*_shift(theme.accent, -10), 220))
    draw.polygon(
        [(int(w * 0.36), handle_y - 14), (int(w * 0.44), handle_y + 9), (int(w * 0.36), handle_y + 32)],
        fill=(*_shift(theme.accent, -5), 220),
    )
    overlay = layer.convert("RGBA")
    if scene in {"hero", "services"}:
        overlay = _figures(
            overlay,
            [(int(w * 0.22), int(h * 0.66), 1.0), (int(w * 0.32), int(h * 0.64), 0.9)],
            _shift(theme.sky, -20),
        )
    img = Image.alpha_composite(base.convert("RGBA"), overlay)
    return _finish_compose(img.convert("RGB"), theme, scene, rng, bokeh_palette=(theme.mid, theme.ground), bokeh_count=8)


def paint_pizza_local_eats(
    scene: str, size: tuple[int, int], rng: random.Random, theme: TemplateTheme
) -> Image.Image:
    w, h = size
    base = vertical_gradient(size, ((0.0, _shift(theme.sky, -30)), (0.35, theme.mid), (1.0, _shift(theme.ground, -35))))
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.rectangle((0, int(h * 0.55), w, h), fill=(*_shift(theme.ground, -40), 255))
    for i in range(4):
        tx = 60 + i * (w // 4)
        draw.rounded_rectangle((tx, int(h * 0.58), tx + 140, int(h * 0.72)), radius=18, fill=(*_shift(theme.accent, 20), 200))
    oven_x, oven_y = int(w * 0.62), int(h * 0.28)
    draw.rounded_rectangle((oven_x, oven_y, oven_x + 220, oven_y + 180), radius=24, fill=(*theme.accent, 230))
    draw.ellipse((oven_x + 50, oven_y + 50, oven_x + 170, oven_y + 140), fill=(255, 170, 70, 180))
    # Pizza slices and toppings motif for obvious restaurant context.
    for px, py in [(int(w * 0.22), int(h * 0.42)), (int(w * 0.34), int(h * 0.4)), (int(w * 0.46), int(h * 0.44))]:
        draw.polygon([(px, py), (px + 84, py + 20), (px + 20, py + 92)], fill=(232, 178, 88, 200))
        draw.ellipse((px + 22, py + 22, px + 38, py + 38), fill=(176, 38, 38, 220))
        draw.ellipse((px + 48, py + 38, px + 62, py + 52), fill=(176, 38, 38, 220))
    img = Image.alpha_composite(base.convert("RGBA"), layer)
    img = _sun_glow(img, (oven_x + 110, oven_y + 95), 120, (255, 150, 60), 110)
    return _finish_compose(
        img.convert("RGB"),
        theme,
        scene,
        rng,
        bokeh_palette=((255, 200, 120), theme.accent, theme.mid),
        bokeh_count=18,
    )


def paint_cloudcare_it(
    scene: str, size: tuple[int, int], rng: random.Random, theme: TemplateTheme
) -> Image.Image:
    w, h = size
    base = vertical_gradient(size, ((0.0, theme.sky), (0.5, theme.mid), (1.0, theme.ground)))
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.rectangle((0, int(h * 0.62), w, h), fill=(*_shift(theme.ground, 10), 255))
    for i in range(3):
        sx = 80 + i * (w // 3)
        draw.rounded_rectangle((sx, int(h * 0.2), sx + 280, int(h * 0.62)), radius=8, fill=(*_shift(theme.sky, 45), 230))
        draw.rectangle((sx + 16, int(h * 0.28), sx + 264, int(h * 0.52)), fill=(60, 140, 210, 120))
    draw.rectangle((int(w * 0.08), int(h * 0.12), int(w * 0.92), int(h * 0.18)), fill=(*theme.accent, 80))
    # Cloud/network symbols for managed IT alignment.
    for cx, cy in [(int(w * 0.24), int(h * 0.16)), (int(w * 0.5), int(h * 0.16)), (int(w * 0.76), int(h * 0.16))]:
        draw.ellipse((cx - 52, cy - 24, cx + 52, cy + 24), fill=(*_shift(theme.sky, 52), 180))
        draw.ellipse((cx - 26, cy - 36, cx + 26, cy + 12), fill=(*_shift(theme.sky, 45), 180))
        draw.rectangle((cx - 4, cy + 20, cx + 4, cy + 38), fill=(*theme.accent, 190))
    img = Image.alpha_composite(base.convert("RGBA"), layer)
    if scene == "about":
        img = _figures(
            img,
            [(w // 5, int(h * 0.7), 1.0), (2 * w // 5, int(h * 0.68), 1.05), (3 * w // 5, int(h * 0.71), 0.95)],
            _shift(theme.sky, 60),
        )
    return _finish_compose(img.convert("RGB"), theme, scene, rng, bokeh_palette=(theme.mid, theme.accent), bokeh_count=12)


def paint_mountain_lodge(
    scene: str, size: tuple[int, int], rng: random.Random, theme: TemplateTheme
) -> Image.Image:
    w, h = size
    base = vertical_gradient(size, ((0.0, _shift(theme.sky, 20)), (0.38, theme.mid), (0.7, theme.ground), (1.0, _shift(theme.ground, -12))))
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    peaks = [0.32, 0.4, 0.48]
    for i, pr in enumerate(peaks):
        px = int(w * (0.08 + i * 0.28))
        py = int(h * pr)
        draw.polygon(
            [(px, py + 120), (px + int(w * 0.26), py), (px + int(w * 0.34), py + 120)],
            fill=(*_shift(theme.mid, -10 * i), 210 - i * 20),
        )
        draw.rectangle((px + 20, py + 40, px + int(w * 0.26), py + 55), fill=(245, 248, 252, 200))
    lodge_x = int(w * 0.34)
    lodge_y = int(h * 0.52)
    lw, lh = int(w * 0.34), int(h * 0.2)
    draw.rectangle((lodge_x, lodge_y, lodge_x + lw, lodge_y + lh), fill=(*_shift(theme.accent, -15), 240))
    draw.polygon(
        [(lodge_x - 10, lodge_y), (lodge_x + lw // 2, lodge_y - lh // 2), (lodge_x + lw + 10, lodge_y)],
        fill=(*theme.accent, 230),
    )
    for i in range(7):
        tx = 40 + i * 90
        draw.polygon([(tx, h - 120), (tx + 22, h - 200), (tx + 44, h - 120)], fill=(*_shift(theme.mid, -25), 200))
    img = Image.alpha_composite(base.convert("RGBA"), layer)
    img = _sun_glow(img, (int(w * 0.7), int(h * 0.2)), int(min(w, h) * 0.16), (255, 210, 150), 85)
    return _finish_compose(img.convert("RGB"), theme, scene, rng, bokeh_palette=(theme.ground, (255, 230, 180)), bokeh_count=9)


def paint_petcare_studio(
    scene: str, size: tuple[int, int], rng: random.Random, theme: TemplateTheme
) -> Image.Image:
    w, h = size
    base = vertical_gradient(size, ((0.0, theme.sky), (0.45, theme.mid), (1.0, theme.ground)))
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.rectangle((0, int(h * 0.5), w, h), fill=(*_shift(theme.ground, 8), 255))
    draw.rounded_rectangle((int(w * 0.1), int(h * 0.22), int(w * 0.9), int(h * 0.48)), radius=20, fill=(*theme.mid, 120))
    for i, (cx, cy) in enumerate([(w // 4, int(h * 0.62)), (w // 2, int(h * 0.58)), (3 * w // 4, int(h * 0.64))]):
        draw.ellipse((cx - 55, cy - 30, cx + 55, cy + 30), fill=(*_shift(theme.accent, i * 8), 200))
    # Add explicit veterinary cues so the petcare identity is obvious at a glance.
    icon_strip_y = int(h * 0.33)
    _paw(draw, (int(w * 0.28), icon_strip_y), 84, _shift(theme.accent, -10), 210)
    _cross(draw, (int(w * 0.5), icon_strip_y), 86, _shift(theme.sky, -28), 210)
    _heart(draw, (int(w * 0.72), icon_strip_y), 88, _shift(theme.accent, 12), 200)
    if scene == "services":
        _paw(draw, (int(w * 0.2), int(h * 0.72)), 70, _shift(theme.accent, 8), 170)
        _paw(draw, (int(w * 0.8), int(h * 0.72)), 70, _shift(theme.accent, 8), 170)
    if scene == "contact":
        draw.rounded_rectangle((int(w * 0.3), int(h * 0.7), int(w * 0.7), int(h * 0.82)), radius=18, fill=(*_shift(theme.sky, -18), 170))
        _cross(draw, (w // 2, int(h * 0.76)), 62, _shift(theme.accent, -12), 220)
    img = Image.alpha_composite(base.convert("RGBA"), layer)
    if scene in {"hero", "about"}:
        img = _figures(img, [(int(w * 0.35), int(h * 0.55), 1.0), (int(w * 0.55), int(h * 0.53), 1.05)], _shift(theme.sky, -15))
    return _finish_compose(img.convert("RGB"), theme, scene, rng, bokeh_palette=(theme.mid, theme.ground), bokeh_count=11)


def paint_community_impact(
    scene: str, size: tuple[int, int], rng: random.Random, theme: TemplateTheme
) -> Image.Image:
    w, h = size
    base = vertical_gradient(size, ((0.0, theme.sky), (0.5, theme.mid), (1.0, theme.ground)))
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    _rolling_hills(draw, w, h, 0.68, _shift(theme.mid, 10), rng, amplitude=22)
    for i in range(3):
        bx = 80 + i * (w // 3)
        draw.rectangle((bx, int(h * 0.42), bx + 160, int(h * 0.58)), fill=(*_shift(theme.accent, i * 6), 200))
        draw.rectangle((bx + 12, int(h * 0.46), bx + 148, int(h * 0.52)), fill=(*theme.sky, 160))
    if scene in {"hero", "about"}:
        _heart(draw, (int(w * 0.5), int(h * 0.28)), 100, _shift(theme.accent, -10), 170)
    img = Image.alpha_composite(base.convert("RGBA"), layer)
    crowd = [(w // 6, int(h * 0.72), 0.9), (w // 3, int(h * 0.7), 1.0), (w // 2, int(h * 0.68), 1.1), (2 * w // 3, int(h * 0.71), 0.95), (5 * w // 6, int(h * 0.73), 0.88)]
    img = _figures(img, crowd, _shift(theme.accent, -35))
    return _finish_compose(img.convert("RGB"), theme, scene, rng, bokeh_palette=(theme.mid, theme.ground), bokeh_count=7)


def paint_homebase_realty(
    scene: str, size: tuple[int, int], rng: random.Random, theme: TemplateTheme
) -> Image.Image:
    w, h = size
    base = vertical_gradient(size, ((0.0, theme.sky), (0.42, theme.mid), (1.0, theme.ground)))
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    hx = int(w * 0.22)
    hy = int(h * 0.36)
    hw, hh = int(w * 0.5), int(h * 0.3)
    draw.rectangle((hx, hy, hx + hw, hy + hh), fill=(*_shift(theme.ground, 20), 245))
    draw.polygon([(hx - 16, hy), (hx + hw // 2, hy - hh // 2), (hx + hw + 16, hy)], fill=(*theme.accent, 230))
    for i in range(4):
        wx = hx + 40 + i * 90
        draw.rectangle((wx, hy + 40, wx + 50, hy + 90), fill=(180, 210, 235, 160))
    if scene in {"hero", "services"}:
        # "For sale" sign cue to anchor real-estate identity.
        sign_x = int(w * 0.78)
        sign_y = int(h * 0.38)
        draw.rectangle((sign_x, sign_y, sign_x + 10, sign_y + 170), fill=(*_shift(theme.accent, -25), 230))
        draw.rounded_rectangle((sign_x - 90, sign_y + 24, sign_x + 72, sign_y + 88), radius=10, fill=(*_shift(theme.sky, 40), 220))
    _rolling_hills(draw, w, h, 0.72, _shift(theme.mid, 15), rng, amplitude=18)
    img = Image.alpha_composite(base.convert("RGBA"), layer)
    if scene == "about":
        img = _figures(img, [(int(w * 0.72), int(h * 0.62), 1.05)], _shift(theme.accent, -20))
    return _finish_compose(img.convert("RGB"), theme, scene, rng, bokeh_palette=(theme.mid, (255, 248, 230)), bokeh_count=8)


def paint_autoworks_garage(
    scene: str, size: tuple[int, int], rng: random.Random, theme: TemplateTheme
) -> Image.Image:
    w, h = size
    base = vertical_gradient(size, ((0.0, _shift(theme.sky, -15)), (0.55, theme.mid), (1.0, theme.ground)))
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.rectangle((0, 0, w, int(h * 0.35)), fill=(*_shift(theme.sky, 25), 255))
    bay_y = int(h * 0.38)
    draw.rectangle((int(w * 0.08), bay_y, int(w * 0.92), h), fill=(*_shift(theme.ground, 12), 255))
    car_x, car_y = int(w * 0.28), int(h * 0.52)
    draw.rounded_rectangle((car_x, car_y, car_x + 340, car_y + 110), radius=18, fill=(*_shift(theme.mid, 20), 245))
    draw.ellipse((car_x + 40, car_y + 80, car_x + 90, car_y + 120), fill=(30, 32, 38, 255))
    draw.ellipse((car_x + 250, car_y + 80, car_x + 300, car_y + 120), fill=(30, 32, 38, 255))
    draw.rectangle((int(w * 0.08), bay_y, int(w * 0.92), bay_y + 8), fill=(*theme.accent, 220))
    # Service stripe + wrench-like silhouette.
    draw.rectangle((int(w * 0.12), int(h * 0.3), int(w * 0.62), int(h * 0.33)), fill=(*_shift(theme.accent, 12), 220))
    draw.rectangle((int(w * 0.62), int(h * 0.285), int(w * 0.74), int(h * 0.345)), fill=(*_shift(theme.accent, 2), 215))
    img = Image.alpha_composite(base.convert("RGBA"), layer)
    img = _sun_glow(img, (int(w * 0.55), int(h * 0.32)), 90, (255, 200, 160), 70)
    if scene in {"hero", "services"}:
        img = _figures(img, [(int(w * 0.62), int(h * 0.58), 1.0)], _shift(theme.ground, 80))
    return _finish_compose(img.convert("RGB"), theme, scene, rng, bokeh_palette=(theme.accent, theme.mid), bokeh_count=10)


def paint_wellness_local(
    scene: str, size: tuple[int, int], rng: random.Random, theme: TemplateTheme
) -> Image.Image:
    w, h = size
    base = vertical_gradient(size, ((0.0, theme.sky), (0.48, theme.mid), (1.0, theme.ground)))
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.rectangle((int(w * 0.55), 0, w, h), fill=(*_shift(theme.mid, 35), 90))
    draw.rounded_rectangle((int(w * 0.12), int(h * 0.25), int(w * 0.72), int(h * 0.7)), radius=22, fill=(*theme.ground, 240))
    draw.rounded_rectangle((int(w * 0.2), int(h * 0.35), int(w * 0.45), int(h * 0.55)), radius=16, fill=(*_shift(theme.mid, 25), 200))
    _cross(draw, (int(w * 0.325), int(h * 0.45)), 80, _shift(theme.accent, -15), 210)
    _heart(draw, (int(w * 0.63), int(h * 0.35)), 70, _shift(theme.mid, -12), 150)
    img = Image.alpha_composite(base.convert("RGBA"), layer)
    if scene in {"hero", "about"}:
        img = _figures(
            img,
            [(int(w * 0.3), int(h * 0.58), 1.0), (int(w * 0.42), int(h * 0.56), 0.95)],
            _shift(theme.accent, -25),
        )
    return _finish_compose(img.convert("RGB"), theme, scene, rng, bokeh_palette=(theme.mid, theme.ground), bokeh_count=9)


THEMES: list[TemplateTheme] = [
    TemplateTheme("greenfield-farm", "Farm & orchard", _rgb(120, 175, 220), _rgb(72, 130, 82), _rgb(46, 92, 58), _rgb(139, 90, 52), 0.18, paint_greenfield_farm),
    TemplateTheme("tradepro-local", "Contractor trades", _rgb(175, 198, 220), _rgb(88, 108, 128), _rgb(210, 214, 220), _rgb(232, 118, 42), 0.08, paint_tradepro_local),
    TemplateTheme("pizza-local-eats", "Restaurant", _rgb(55, 38, 32), _rgb(120, 72, 58), _rgb(32, 24, 22), _rgb(210, 92, 48), 0.28, paint_pizza_local_eats),
    TemplateTheme("cloudcare-it", "IT & SaaS", _rgb(210, 222, 235), _rgb(120, 155, 195), _rgb(236, 240, 246), _rgb(16, 185, 129), 0.05, paint_cloudcare_it),
    TemplateTheme("mountain-lodge", "Lodge & tourism", _rgb(130, 175, 220), _rgb(72, 108, 145), _rgb(58, 78, 62), _rgb(168, 118, 72), 0.22, paint_mountain_lodge),
    TemplateTheme("petcare-studio", "Pet care clinic", _rgb(215, 232, 228), _rgb(130, 188, 175), _rgb(238, 244, 242), _rgb(42, 128, 118), 0.1, paint_petcare_studio),
    TemplateTheme("community-impact", "Nonprofit", _rgb(150, 198, 235), _rgb(95, 155, 125), _rgb(228, 236, 228), _rgb(52, 118, 185), 0.12, paint_community_impact),
    TemplateTheme("homebase-realty", "Real estate", _rgb(165, 198, 225), _rgb(108, 125, 138), _rgb(228, 220, 208), _rgb(148, 118, 88), 0.14, paint_homebase_realty),
    TemplateTheme("autoworks-garage", "Auto garage", _rgb(90, 98, 108), _rgb(48, 54, 62), _rgb(175, 180, 188), _rgb(198, 58, 45), 0.06, paint_autoworks_garage),
    TemplateTheme("wellness-local", "Wellness clinic", _rgb(220, 230, 228), _rgb(165, 192, 182), _rgb(240, 244, 242), _rgb(98, 140, 128), 0.15, paint_wellness_local),
]


def create_scene(theme: TemplateTheme, scene: str, size: tuple[int, int] = (1920, 1200)) -> Image.Image:
    rng = _seed(theme, scene)
    if scene == "hero":
        render_size = (int(size[0] * HERO_RENDER_SCALE), int(size[1] * HERO_RENDER_SCALE))
        rendered = theme.painter(scene, render_size, rng, theme)
        return rendered.resize(size, Image.Resampling.LANCZOS)
    return theme.painter(scene, size, rng, theme)


def export_variant(
    src: Image.Image,
    out_path: Path,
    size: tuple[int, int],
    crop_box: tuple[float, float, float, float] | None = None,
    *,
    sharpen: float = 1.0,
    quality: int = 88,
):
    if crop_box:
        w, h = src.size
        crop = src.crop((int(w * crop_box[0]), int(h * crop_box[1]), int(w * crop_box[2]), int(h * crop_box[3])))
        image = crop.resize(size, Image.Resampling.LANCZOS)
    else:
        image = src.resize(size, Image.Resampling.LANCZOS)
    if sharpen > 1.0:
        image = ImageEnhance.Sharpness(image).enhance(sharpen)
    image = ImageEnhance.Color(image).enhance(1.03)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path, "WEBP", quality=max(quality, WEBP_QUALITY), method=6)


def generate_template_assets(theme: TemplateTheme) -> int:
    target = OUTPUT_ROOT / theme.slug
    target.mkdir(parents=True, exist_ok=True)
    written = 0

    print(f"    rendering hero...", flush=True)
    hero = create_scene(theme, "hero", (1920, 1200))
    export_variant(hero, target / "hero.webp", (1600, 900), sharpen=1.12)
    export_variant(hero, target / "hero-mobile.webp", (900, 1200), (0.12, 0.0, 0.88, 1.0), sharpen=1.14)
    export_variant(hero, target / "thumbnail.webp", (800, 480), sharpen=1.1)
    export_variant(hero, target / "preview.webp", (1440, 900), (0.0, 0.02, 1.0, 0.9), sharpen=1.1)
    written += 4

    for page_scene, filename in (
        ("about", "about.webp"),
        ("services", "services.webp"),
        ("contact", "contact.webp"),
    ):
        print(f"    rendering {page_scene}...", flush=True)
        page_image = create_scene(theme, page_scene, PAGE_RENDER_SIZE)
        export_variant(page_image, target / filename, (1280, 720), sharpen=1.08)
        written += 1

    for index in range(1, GALLERY_SCENE_COUNT + 1):
        print(f"    rendering gallery-{index}...", flush=True)
        gallery_scene = create_scene(theme, f"gallery-{index}", GALLERY_RENDER_SIZE)
        export_variant(gallery_scene, target / f"gallery-{index}.webp", (1280, 720), sharpen=1.1)
        written += 1

    for scene_name in INLINE_SCENE_NAMES:
        print(f"    rendering {scene_name}...", flush=True)
        inline_scene = create_scene(theme, scene_name, GALLERY_RENDER_SIZE)
        export_variant(inline_scene, target / f"{scene_name}.webp", (1280, 720), sharpen=1.08)
        written += 1

    return written


def main():
    import sys

    slugs = [theme.slug for theme in THEMES]
    if len(sys.argv) > 1:
        requested = {arg.strip() for arg in sys.argv[1:]}
        themes = [theme for theme in THEMES if theme.slug in requested]
        if not themes:
            raise SystemExit(f"No matching slugs. Available: {', '.join(slugs)}")
    else:
        themes = THEMES

    total_files = 0
    for theme in themes:
        print(f"  {theme.slug}:", flush=True)
        total_files += generate_template_assets(theme)
    print(
        f"Generated {total_files} photorealistic WebP files "
        f"for {len(themes)} template(s) in {OUTPUT_ROOT}"
    )


if __name__ == "__main__":
    main()
