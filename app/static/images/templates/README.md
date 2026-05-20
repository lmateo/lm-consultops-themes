# Template Image Structure

Create the following folder and file pattern for each template slug:

```text
app/static/images/templates/<template-slug>/
├── hero.webp
├── hero-mobile.webp
├── thumbnail.webp
├── preview.webp
├── gallery-1.webp
├── gallery-2.webp
└── gallery-3.webp
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

Use royalty-free AI generations based on prompt files in `assets/prompts/`.

## Regenerate from AI sources

1. Place or generate source PNGs in `assets/ai-sources/` as `<slug>-ai.png`.
2. Run:

```bash
python assets/scripts/process_ai_template_images.py
```

This overwrites all required WebP files for every template slug.
