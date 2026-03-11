# Joyno SEO Auditor Tool

Joyno SEO Auditor Tool is a production-minded FastAPI web app for crawling a website, surfacing SEO and performance issues, and exporting HTML, CSV, and PDF audit reports.

## Architecture Summary

- FastAPI handles server-rendered web routes and lightweight JSON endpoints.
- Jinja2 templates provide the desktop-first dashboard UI, styled with Tailwind CSS and a small custom stylesheet.
- SQLAlchemy models persist projects, audit runs, page results, issues, and asset records in PostgreSQL.
- Redis + RQ run long-running audits in the production deployment path.
- The audit engine is a separate package for crawling, parsing, analyzing, scoring, and report generation.
- PageSpeed Insights is integrated for homepage performance scoring in V1.
- Playwright is supported for pages that need JavaScript rendering.

## Folder Tree

```text
seo_auditor_app/
  app/
    audit_engine/
      analyzers/
      crawler/
      integrations/
      parsers/
      reporters/
      scoring/
      utils/
    models/
    routes/
    schemas/
    services/
    static/
    templates/
    workers/
    config.py
    db.py
    dependencies.py
    logging.py
    main.py
  alembic/
    versions/
  docker/
    postgres-init/
  scripts/
  tests/
  .env.example
  alembic.ini
  docker-compose.yml
  pyproject.toml
  README.md
```

## MVP Scope

- Dashboard page
- New Audit page
- Audit progress page with polling
- Audit results page with tabs
- Audit history page
- HTML, CSV, and PDF report downloads
- Website crawling with same-domain defaults
- Metadata, heading, link, image, and asset checks
- Homepage PageSpeed analysis

## Local Setup

1. Copy `.env.example` to `.env`. The app reads namespaced `SEO_AUDITOR_*` variables only.
2. Start services with `docker compose up --build`.
3. Run migrations with `docker compose exec web alembic upgrade head`.
4. Open `http://localhost:8000`.
5. Optional: seed demo data with `docker compose exec web python scripts/seed_dev_data.py`.

## Development Commands

```bash
docker compose up --build
docker compose exec web alembic upgrade head
docker compose exec web pytest
docker compose exec web python scripts/seed_dev_data.py
```

## Hosted Deployment

You do not need Docker installed locally to publish this app.

The repository now includes [render.yaml](C:\Users\Joyno IT\Desktop\Python\seo_auditor_app\render.yaml) for a hosted deployment with:

- one free Render web service
- inline audit execution in the web process
- SQLite storage inside the container
- local report files inside the container

This is the zero-cost deployment path. It avoids paid worker infrastructure, but it has real tradeoffs:

1. Audits run inside the web app process, so long audits can make the free instance feel slow.
2. SQLite and local report files are stored on Render's ephemeral filesystem, so they can disappear after a redeploy or restart.
3. This is suitable for a free public MVP or demo, not durable production storage.

Before deploying, prepare:

1. A Render account connected to the repository
2. The web service `SEO_AUDITOR_BASE_URL` value after Render assigns the URL
3. `SEO_AUDITOR_PAGESPEED_API_KEY` optionally

Notes:

- The web startup script runs `alembic upgrade head` before boot.
- `render.yaml` is the free Render blueprint.
- [render.production.yaml](C:\Users\Joyno IT\Desktop\Python\seo_auditor_app\render.production.yaml) keeps the original multi-service architecture for paid deployments.
- The zero-cost blueprint sets `SEO_AUDITOR_EXECUTION_BACKEND=inline`.
- Local Docker development still uses PostgreSQL, Redis, and the worker service.

## Core Routes

- `GET /dashboard`
- `GET /audits/new`
- `POST /audits`
- `GET /audits/{audit_id}`
- `GET /audits/{audit_id}/status`
- `GET /audits/{audit_id}/reports?format=html|csv|pdf`
- `GET /history`
- `GET /reports`
- `GET /api/health`

## Notes

- Tailwind is loaded from the CDN for V1 speed of development.
- Reports are stored on disk in the `reports/` directory.
- The current MVP assumes a single local user and auto-creates a default user record on demand.
- The PageSpeed API key is optional but recommended for higher request reliability.
