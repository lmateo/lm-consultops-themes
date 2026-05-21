# Template Image Structure

Each template slug has **page-specific** royalty-free photorealistic imagery.

```text
app/static/images/templates/<template-slug>/
├── hero.webp           # Home — wide hero scene
├── hero-mobile.webp    # Home — portrait hero crop
├── thumbnail.webp      # Marketplace cards & list rows
├── preview.webp        # Detail page & live preview frame
├── about.webp          # About page banner
├── services.webp       # Services page banner
├── contact.webp        # Contact page banner
├── gallery-1.webp … gallery-12.webp  # Unique gallery/section photos
├── team.webp           # Team/staff sections
├── blog.webp           # Blog/news cards
├── feature.webp        # Feature/benefit blocks
└── showcase.webp       # Portfolio/showcase sections
```

Expected slugs:

- `greenfield-farm`
- `tradepro-local`
- `pizza-local-eats`
- `cloudcare-it`
- `mountain-lodge`
- `petcare-studio`
- `community-impact`
- `homebase-realty`
- `autoworks-garage`
- `wellness-local`

## Prompts must match live preview (Crafto)

Marketplace titles (e.g. GreenField Farm) differ from Crafto preview demos (e.g. Green Energy).  
Prompts in `assets/prompts/<slug>.txt` and `PEXELS_QUERIES` in `fetch_photoreal_template_images.py` are keyed by **slug** but describe the **Crafto preview subject** (see `app/services/crafto_demos.py`).

## Regenerate photorealistic photos (recommended)

Downloads unique photorealistic scenes per template (Pexels when `PEXELS_API_KEY` is set, else prompt-based Pollinations, then Picsum fallback).

```bash
python assets/scripts/fetch_photoreal_template_images.py
```

One template:

```bash
python assets/scripts/fetch_photoreal_template_images.py cloudcare-it
```

### Industry-specific search (optional)

Set `PEXELS_API_KEY` in `.env` to use the [Pexels API](https://www.pexels.com/api/) for industry-targeted stock photos instead of random Unsplash seeds.

## Regenerate from AI source PNG (optional)

1. Generate or place source PNGs in `assets/ai-sources/` as `<slug>-ai.png` (prompts in `assets/prompts/<slug>.txt`).
2. Run:

```bash
python assets/scripts/process_ai_template_images.py
```

## Procedural fallback (offline only)

```bash
python assets/scripts/generate_template_images.py
```

Use only when network downloads are unavailable. Output is illustrative, not photographic.
