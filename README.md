# Mateo ConsultOps Themes

Premium SaaS-style website template store built with FastAPI, Jinja2, Tailwind CSS, Alpine.js, and SQLAlchemy 2.x.

## Features

- Homepage with featured, best-selling, and new templates; browse at `/popular`
- ThemeForest-inspired browse and filter UX (original implementation)
- Category and industry landing pages
- Template detail pages with gallery, features, and upsells
- Live preview frame with responsive viewport controls
- Stripe Checkout flow with purchase record creation
- Secure signed download links for paid theme packages
- Full website source package per theme (home, about, services, pricing, contact)
- My Downloads self-service page by purchase email
- Stripe webhook event log for auditability and idempotency
- Retry-safe fulfillment email workflow after successful payment
- Services pages (setup and customization)
- Admin dashboard overview for store operations
- SEO-ready page metadata and semantic HTML

## Stack

- FastAPI
- Jinja2
- Tailwind CSS (CDN)
- Alpine.js
- SQLAlchemy 2.x
- Alembic-ready structure
- SQLite for local development, PostgreSQL-ready configuration

## Quick Start

1. Create and activate a virtualenv.
1. Install dependencies:

```bash
pip install -r requirements.txt
```

1. Copy `.env.example` to `.env` and set:
   - `STRIPE_SECRET_KEY`
   - `STRIPE_WEBHOOK_SECRET` (recommended for webhook signature verification)
   - SMTP values (`SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`) to enable fulfillment emails
   - `CONSULTOPS_BASE_URL` and `INTEGRATION_API_KEY` to enable the contact form (proxies to ConsultOps `/api/integrations/contacts`)
1. Seed development data:

```bash
python -m app.seed.seed
```

1. Run the app:

```bash
uvicorn app.main:app --reload
```

1. Open [http://localhost:8000](http://localhost:8000).

1. Optional (recommended): run Stripe CLI in another terminal:

```bash
stripe listen --forward-to localhost:8000/webhooks/stripe
```

## Docker

On first `.\docker.ps1 up`, a `.env` file is created automatically from `.env.example` (with `BASE_URL` set for port 8010). The stack seeds the database on startup and serves the app at **[http://localhost:8010](http://localhost:8010)** (container port 8000).

**Windows (PowerShell)** — from the repo root:

```powershell
.\docker.ps1 up        # start (detached)
.\docker.ps1 down      # stop
.\docker.ps1 restart   # down then up
.\docker.ps1 rebuild   # no-cache image rebuild + start
.\docker.ps1 logs      # follow web logs
.\docker.ps1 clean     # stop and remove volumes
```

**macOS / Linux / Git Bash:**

```bash
./scripts/docker.sh up
./scripts/docker.sh down
./scripts/docker.sh restart
```

**Make** (if `make` is installed): `make up`, `make down`, `make restart`, `make rebuild`, `make logs`, `make clean`.

Raw Compose still works: `docker compose up -d` and `docker compose down`.

## Template Images

Template visuals are stored locally under `app/static/images/templates/<slug>/` with **distinct images per page** (hero, about, services, contact, galleries, thumbnail).

Regenerate royalty-free procedural WebP sets:

```bash
python assets/scripts/generate_template_images.py
```

Optional: regenerate from AI source PNGs in `assets/ai-sources/`:

```bash
python assets/scripts/process_ai_template_images.py
```

## Structure

```text
mateo-consultops-themes/
├── app/
│   ├── main.py
│   ├── core/
│   ├── models/
│   ├── routers/
│   ├── services/
│   ├── schemas/
│   ├── templates/
│   ├── static/
│   ├── seed/
│   └── utils/
├── alembic/
├── tests/
├── assets/
├── docker.ps1
├── scripts/docker.ps1
├── scripts/docker.sh
├── Makefile
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```
