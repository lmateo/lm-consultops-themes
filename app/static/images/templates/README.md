# Template Image Structure

Each template slug has **page-specific** royalty-free photorealistic procedural imagery (generated locally, no stock licensing).

```text
app/static/images/templates/<template-slug>/
├── hero.webp           # Home — wide hero scene
├── hero-mobile.webp    # Home — portrait hero crop
├── thumbnail.webp      # Marketplace cards & list rows
├── preview.webp        # Detail page & live preview frame
├── about.webp          # About page banner
├── services.webp       # Services page banner
├── contact.webp        # Contact page banner
├── gallery-1.webp … gallery-12.webp  # Unique section/gallery scenes
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

## Regenerate from AI sources (recommended)

1. Generate or place source PNGs in `assets/ai-sources/` as `<slug>-ai.png` (prompts in `assets/prompts/<slug>.txt`).
2. Run:

```bash
python assets/scripts/process_ai_template_images.py
```

Exports hero, thumbnail, preview, page banners, 12 gallery scenes, and inline section WebPs from each source.

## Regenerate procedural sets (fallback)

```bash
python assets/scripts/generate_template_images.py
```

Creates industry-specific photographic-style scenes per page plus 12 gallery variants and inline section images when AI sources are unavailable. The generator applies film grain, bloom, atmospheric haze, vignette, and per-scene camera profiles so each WebP looks like a distinct photograph.

Regenerate all templates:

```bash
python assets/scripts/generate_template_images.py
```

Regenerate one slug:

```bash
python assets/scripts/generate_template_images.py cloudcare-it
```
