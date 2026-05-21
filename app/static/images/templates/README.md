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
├── gallery-1.webp      # Home gallery / services scene
├── gallery-2.webp      # Home gallery / about scene
└── gallery-3.webp      # Home gallery / contact scene
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

Exports hero, thumbnail, preview, page banners, and gallery WebPs from each source.

## Regenerate procedural sets (fallback)

```bash
python assets/scripts/generate_template_images.py
```

Creates industry-specific photographic-style scenes per page when AI sources are unavailable.
