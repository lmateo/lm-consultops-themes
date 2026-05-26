"""
Download high-resolution royalty-free photorealistic photos for live preview templates.

Sources (in order):
1. Pexels API — royalty-free stock photos (set PEXELS_API_KEY in .env)
2. Picsum — real Unsplash-sourced photographs (fast, royalty-free)
3. Pollinations — AI photorealistic renders from assets/prompts/{slug}.txt (slow fallback)

Each scene is a unique photograph, then exported to the WebP set under
app/static/images/templates/<slug>/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import ssl
import time
from io import BytesIO
from pathlib import Path
from urllib.error import URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from PIL import Image, ImageEnhance, ImageOps

OUTPUT_ROOT = Path("app/static/images/templates")
PROMPTS_DIR = Path("assets/prompts")

SLUGS = (
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
)

GALLERY_SCENE_COUNT = 12
INLINE_SCENES = ("team", "blog", "feature", "showcase")
PAGE_SCENES = ("hero", "about", "services", "contact")

# scene -> list of (output filename, width, height, crop box)
EXPORTS: dict[str, list[tuple[str, int, int, tuple[float, float, float, float]]]] = {
    "hero": [
        ("hero.webp", 1600, 900, (0.0, 0.05, 1.0, 0.88)),
        ("hero-mobile.webp", 900, 1200, (0.12, 0.0, 0.88, 1.0)),
        ("thumbnail.webp", 800, 480, (0.0, 0.1, 1.0, 0.82)),
        ("preview.webp", 1440, 900, (0.02, 0.04, 0.98, 0.9)),
    ],
    "about": [("about.webp", 1280, 720, (0.05, 0.08, 0.92, 0.94))],
    "services": [("services.webp", 1280, 720, (0.0, 0.02, 0.95, 0.88))],
    "contact": [("contact.webp", 1280, 720, (0.03, 0.12, 0.97, 0.98))],
}
for index in range(1, GALLERY_SCENE_COUNT + 1):
    EXPORTS[f"gallery-{index}"] = [
        (f"gallery-{index}.webp", 1280, 720, (0.02, 0.04, 0.96, 0.92)),
    ]
for name in INLINE_SCENES:
    EXPORTS[name] = [(f"{name}.webp", 1280, 720, (0.04, 0.06, 0.96, 0.94))]

SCENE_MODIFIERS: dict[str, str] = {
    "hero": "cinematic wide hero banner, golden hour, ultra photorealistic, 8k, DSLR",
    "about": "authentic team and workspace, documentary photography, natural expressions",
    "services": "service in action, commercial photography, crisp detail, shallow depth of field",
    "contact": "welcoming reception area, inviting natural light, professional photography",
    "team": "professional team portrait, friendly staff, office or field environment",
    "blog": "editorial blog feature photo, storytelling composition",
    "feature": "feature highlight close-up, premium brand photography",
    "showcase": "portfolio showcase scene, wide composition, high-end marketing photo",
}

SCENE_ALIGNMENT_DIRECTIVES: dict[str, str] = {
    "hero": (
        "Keep the primary subject inside the center safe area (middle 60% width and middle 55% height). "
        "Leave clear breathing room on both horizontal edges for responsive crops."
    ),
    "about": (
        "Frame people and key objects with headroom and side margins; avoid placing faces or hands against frame edges."
    ),
    "services": (
        "Center the main service action and preserve generous side margins so 16:9 and 4:3 crops remain balanced."
    ),
    "contact": (
        "Use centered architectural/interior framing with uncluttered edge space for text overlays and responsive crops."
    ),
    "team": "Keep the group centered with even spacing and no person clipped by the frame boundaries.",
    "blog": "Compose with one clear focal subject centered and supporting elements distributed symmetrically.",
    "feature": "Place the featured object in the center third with clean negative space around it.",
    "showcase": "Use a balanced wide composition with the focal subject centered and crop-safe margins.",
}

GLOBAL_QUALITY_DIRECTIVE = (
    "Photorealistic commercial photography, consistent lens style and lighting across the full template set, "
    "no text, no letters, no logos, no watermark, no UI mockups, no collage, no split-screen."
)

# Queries aligned to marketplace brand subjects (not underlying Crafto demo keys).
PEXELS_QUERIES: dict[str, dict[str, str]] = {
    "greenfield-farm": {
        "hero": "apple orchard farm rows autumn harvest",
        "about": "farm family portrait rural barn",
        "services": "u-pick fruit farm visitors baskets",
        "contact": "farm stand fresh produce wooden display",
        "team": "farmers field harvest workers smiling",
        "blog": "farm to table outdoor dinner sunset",
        "feature": "CSA harvest box fresh vegetables",
        "showcase": "pastoral farm landscape barn aerial",
    },
    "tradepro-local": {
        "hero": "HVAC technician rooftop unit repair",
        "about": "electrician residential panel service",
        "services": "roofer inspecting shingles residential",
        "contact": "trades company office dispatch",
        "team": "tradespeople uniforms tool belts group",
        "blog": "plumber fixing pipes residential kitchen",
        "feature": "branded service van suburban home",
        "showcase": "residential home improvement construction",
    },
    "pizza-local-eats": {
        "hero": "pizza restaurant wood fired oven",
        "about": "restaurant kitchen chef team",
        "services": "pizza pasta dishes restaurant",
        "contact": "restaurant interior dining",
        "team": "restaurant staff smiling",
        "blog": "food photography italian restaurant",
        "feature": "fresh pizza close up",
        "showcase": "restaurant cozy interior evening",
    },
    "cloudcare-it": {
        "hero": "modern office technology cybersecurity",
        "about": "business team meeting technology office",
        "services": "data center servers cloud computing",
        "contact": "office reception modern tech",
        "team": "diverse tech team office",
        "blog": "software dashboard analytics screen",
        "feature": "laptop network security professional",
        "showcase": "technology workspace monitors",
    },
    "mountain-lodge": {
        "hero": "mountain lodge cabin snowy peaks",
        "about": "hotel staff luxury lodge",
        "services": "hotel room suite mountain view",
        "contact": "lodge lobby fireplace cozy",
        "team": "hospitality team hotel",
        "blog": "mountain resort activities hiking",
        "feature": "cabin deck mountain sunrise",
        "showcase": "resort aerial forest mountains",
    },
    "petcare-studio": {
        "hero": "veterinary clinic dog cat pet care",
        "about": "veterinarian team pet clinic staff",
        "services": "pet wellness exam veterinary room",
        "contact": "pet clinic reception welcoming",
        "team": "veterinary staff pets smiling",
        "blog": "pet health dog cat wellness",
        "feature": "veterinarian examining puppy kitten",
        "showcase": "modern pet clinic building exterior",
    },
    "community-impact": {
        "hero": "community volunteers charity event",
        "about": "nonprofit team diverse volunteers",
        "services": "food bank community support",
        "contact": "community center gathering",
        "team": "volunteers smiling group",
        "blog": "charity donation community",
        "feature": "helping hands community outreach",
        "showcase": "outdoor fundraiser community",
    },
    "homebase-realty": {
        "hero": "luxury home exterior real estate",
        "about": "real estate agent professional",
        "services": "house for sale modern home",
        "contact": "real estate office interior",
        "team": "realtors team office",
        "blog": "new home keys homeowner",
        "feature": "living room staged home",
        "showcase": "suburban house aerial view",
    },
    "autoworks-garage": {
        "hero": "auto repair mechanic car lift garage",
        "about": "auto mechanic team portrait shop",
        "services": "brake inspection automotive service bay",
        "contact": "auto shop reception customer counter",
        "team": "ASE certified mechanics group photo",
        "blog": "engine diagnostics scanner OBD vehicle",
        "feature": "oil change automotive service close up",
        "showcase": "clean auto repair garage interior",
    },
    "wellness-local": {
        "hero": "doctor patient consultation medical clinic",
        "about": "healthcare team physician therapist clinic",
        "services": "physical therapy rehabilitation exercise",
        "contact": "medical clinic reception desk modern",
        "team": "healthcare providers group photo clinic",
        "blog": "nutrition coaching healthy lifestyle",
        "feature": "telehealth video consultation doctor",
        "showcase": "modern integrative wellness clinic interior",
    },
}

WEBP_QUALITY = 92
DOWNLOAD_TIMEOUT = 180.0


def _scene_list() -> tuple[str, ...]:
    return (
        *PAGE_SCENES,
        *(f"gallery-{index}" for index in range(1, GALLERY_SCENE_COUNT + 1)),
        *INLINE_SCENES,
    )


def _load_prompt_fields(slug: str) -> dict[str, str]:
    """Load all key: value fields from a prompt file."""
    path = PROMPTS_DIR / f"{slug}.txt"
    fields: dict[str, str] = {}
    if not path.is_file():
        return fields
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip().lower().replace(" ", "_")
            value = value.strip()
            if key and value:
                fields[key] = value
    return fields


def _load_prompt_subject(slug: str) -> str:
    fields = _load_prompt_fields(slug)
    return fields.get("subject", f"Professional {slug.replace('-', ' ')} business photography")


def _gallery_modifier(index: int) -> str:
    variants = (
        "wide environmental establishing shot",
        "medium shot lifestyle detail",
        "close-up product and texture detail",
        "overhead flat lay composition",
        "candid customer interaction moment",
        "architectural interior wide angle",
        "outdoor natural light scene",
        "evening ambient mood lighting",
        "hands-on service action shot",
        "behind the scenes workspace",
        "seasonal campaign hero detail",
        "trust and quality craftsmanship focus",
    )
    return variants[(index - 1) % len(variants)]


def _build_prompt(slug: str, scene: str) -> str:
    fields = _load_prompt_fields(slug)
    subject = fields.get("subject", f"Professional {slug.replace('-', ' ')} photography")
    lighting = fields.get("lighting", "")
    mood = fields.get("mood", "")
    composition = fields.get("composition", "")
    palette = fields.get("palette", "")
    camera_angle = fields.get("camera_angle", "")
    template_alignment = fields.get("alignment_instructions", "")
    scene_alignment = fields.get(f"{scene}_alignment_instructions", "")
    gallery_alignment = fields.get("gallery_alignment_instructions", "")

    if scene.startswith("gallery-"):
        index = int(scene.split("-", 1)[1])
        modifier = _gallery_modifier(index)
        default_alignment = (
            "Keep the focal subject centered with protected margins so landscape and portrait crops "
            "remain coherent."
        )
    else:
        modifier = SCENE_MODIFIERS.get(scene, "professional marketing photography")
        default_alignment = SCENE_ALIGNMENT_DIRECTIVES.get(
            scene,
            "Use a balanced centered composition with responsive crop safety on all sides.",
        )
    if scene.startswith("gallery-"):
        alignment = scene_alignment or gallery_alignment or template_alignment or default_alignment
    else:
        alignment = scene_alignment or template_alignment or default_alignment

    parts = [subject]
    if lighting:
        parts.append(f"Lighting: {lighting}")
    if mood:
        parts.append(f"Mood: {mood}")
    if composition and scene == "hero":
        parts.append(composition)
    if camera_angle:
        parts.append(camera_angle)
    if palette:
        parts.append(f"Color palette: {palette}")
    parts.append(modifier)
    parts.append(alignment)
    parts.append(GLOBAL_QUALITY_DIRECTIVE)
    return ". ".join(parts) + "."


def _stable_seed(slug: str, scene: str) -> int:
    digest = hashlib.sha256(f"{slug}:{scene}:mateo-preview-v2".encode()).hexdigest()
    return int(digest[:8], 16)


def _pexels_query(slug: str, scene: str) -> str:
    slug_queries = PEXELS_QUERIES.get(slug, {})
    if scene in slug_queries:
        return slug_queries[scene]
    if scene.startswith("gallery-"):
        return slug_queries.get("showcase", _load_prompt_subject(slug))
    return _load_prompt_subject(slug)


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _download_bytes(url: str, headers: dict[str, str] | None = None) -> bytes:
    request = Request(url, headers=headers or {})
    try:
        with urlopen(request, timeout=DOWNLOAD_TIMEOUT, context=_ssl_context()) as response:
            return response.read()
    except (ssl.SSLError, URLError):
        unverified = ssl._create_unverified_context()
        with urlopen(request, timeout=DOWNLOAD_TIMEOUT, context=unverified) as response:
            return response.read()


def _fetch_from_pexels(api_key: str, slug: str, scene: str, width: int, height: int) -> Image.Image | None:
    query = _pexels_query(slug, scene)
    page = 1 + (_stable_seed(slug, scene) % 8)
    params = urlencode(
        {"query": query, "per_page": 1, "page": page, "orientation": "landscape"}
    )
    search_url = f"https://api.pexels.com/v1/search?{params}"
    try:
        raw = _download_bytes(search_url, headers={"Authorization": api_key})
        payload = json.loads(raw.decode("utf-8"))
        photos = payload.get("photos") or []
        if not photos:
            return None
        src = photos[0].get("src") or {}
        photo_url = src.get("original") or src.get("large2x") or src.get("large")
        if not photo_url:
            return None
        image_bytes = _download_bytes(photo_url)
        image = Image.open(BytesIO(image_bytes))
        if image.mode != "RGB":
            image = image.convert("RGB")
        return ImageOps.fit(image, (width, height), Image.Resampling.LANCZOS)
    except (OSError, KeyError, json.JSONDecodeError, ValueError):
        return None


def _fetch_from_pollinations(slug: str, scene: str, width: int, height: int) -> Image.Image | None:
    prompt = _build_prompt(slug, scene)
    seed = _stable_seed(slug, scene)
    encoded = quote(prompt, safe="")
    url = (
        "https://image.pollinations.ai/prompt/"
        f"{encoded}?width={width}&height={height}&seed={seed}&nologo=true&enhance=true"
    )
    try:
        raw = _download_bytes(url)
        image = Image.open(BytesIO(raw))
        if image.mode != "RGB":
            image = image.convert("RGB")
        return image
    except OSError:
        return None


def _fetch_from_picsum(slug: str, scene: str, width: int, height: int) -> Image.Image | None:
    seed = f"{slug}-{scene}"
    url = f"https://picsum.photos/seed/{quote(seed, safe='')}/{width}/{height}"
    try:
        raw = _download_bytes(url)
        image = Image.open(BytesIO(raw))
        if image.mode != "RGB":
            image = image.convert("RGB")
        return image
    except OSError:
        return None


def fetch_scene_image(slug: str, scene: str, *, pexels_key: str | None) -> Image.Image:
    width, height = (1920, 1200) if scene == "hero" else (1600, 1000)
    if pexels_key:
        image = _fetch_from_pexels(pexels_key, slug, scene, width, height)
        if image is not None:
            return image
    # Prompt-based generation before Picsum so live-preview subjects stay on-brand.
    image = _fetch_from_pollinations(slug, scene, width, height)
    if image is not None:
        return image
    image = _fetch_from_picsum(slug, scene, width, height)
    if image is not None:
        return image
    raise RuntimeError(f"Unable to download photo for {slug}/{scene}")


def export_variant(
    src: Image.Image,
    out_path: Path,
    width: int,
    height: int,
    crop_box: tuple[float, float, float, float],
) -> None:
    img_w, img_h = src.size
    crop = src.crop(
        (
            int(img_w * crop_box[0]),
            int(img_h * crop_box[1]),
            int(img_w * crop_box[2]),
            int(img_h * crop_box[3]),
        )
    )
    fitted = ImageOps.fit(crop, (width, height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (width, height), (248, 250, 252))
    canvas.paste(fitted, ((width - fitted.width) // 2, (height - fitted.height) // 2))
    canvas = ImageEnhance.Sharpness(canvas).enhance(1.08)
    canvas = ImageEnhance.Color(canvas).enhance(1.04)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, "WEBP", quality=WEBP_QUALITY, method=6)


def generate_slug_assets(
    slug: str,
    *,
    pexels_key: str | None,
    delay_s: float,
    selected_scenes: set[str] | None = None,
) -> int:
    target = OUTPUT_ROOT / slug
    target.mkdir(parents=True, exist_ok=True)
    written = 0
    scene_cache: dict[str, Image.Image] = {}

    all_scenes = _scene_list()
    if selected_scenes is None:
        scenes_to_download = all_scenes
    else:
        scenes_to_download = tuple(scene for scene in all_scenes if scene in selected_scenes)

    for scene in scenes_to_download:
        print(f"    downloading {scene}...", flush=True)
        scene_cache[scene] = fetch_scene_image(slug, scene, pexels_key=pexels_key)
        if delay_s > 0:
            time.sleep(delay_s)

    for scene, exports in EXPORTS.items():
        if selected_scenes is not None and scene not in selected_scenes:
            continue
        source = scene_cache[scene]
        for filename, width, height, crop in exports:
            export_variant(source, target / filename, width, height, crop)
            written += 1
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slugs", nargs="*", help="Optional template slugs to process")
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Seconds between remote downloads (rate limiting)",
    )
    parser.add_argument(
        "--scenes",
        type=str,
        default="",
        help="Comma-separated scene names to regenerate (e.g. hero,about).",
    )
    parser.add_argument(
        "--hero-only",
        action="store_true",
        help="Shortcut for --scenes hero (updates hero, hero-mobile, thumbnail, preview).",
    )
    args = parser.parse_args()

    selected = args.slugs or list(SLUGS)
    unknown = [slug for slug in selected if slug not in SLUGS]
    if unknown:
        raise SystemExit(f"Unknown slugs: {', '.join(unknown)}")

    pexels_key = os.environ.get("PEXELS_API_KEY", "").strip() or None
    if pexels_key:
        print("Using Pexels API for primary photo source.")
    else:
        print("PEXELS_API_KEY not set — using Pollinations (prompt-based), then Picsum fallback.")

    if args.hero_only and args.scenes.strip():
        raise SystemExit("Use either --hero-only or --scenes, not both.")

    scenes_arg = "hero" if args.hero_only else args.scenes

    selected_scenes: set[str] | None = None
    if scenes_arg.strip():
        requested = {
            scene.strip().lower()
            for scene in scenes_arg.split(",")
            if scene.strip()
        }
        valid = set(_scene_list())
        unknown_scenes = sorted(requested - valid)
        if unknown_scenes:
            raise SystemExit(f"Unknown scenes: {', '.join(unknown_scenes)}")
        selected_scenes = requested
        print(f"Restricting generation to scenes: {', '.join(sorted(selected_scenes))}")

    total = 0
    for slug in selected:
        print(f"  {slug}:", flush=True)
        total += generate_slug_assets(
            slug,
            pexels_key=pexels_key,
            delay_s=args.delay,
            selected_scenes=selected_scenes,
        )

    print(f"Exported {total} photorealistic WebP files to {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
