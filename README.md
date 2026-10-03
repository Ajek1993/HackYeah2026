# KryzIO

AI agent for Kraków residents that aggregates public crisis data (IMGW, Tauron, GIOŚ, Airly, safety guide, shelters) and tells you what to do at your address — before, during and after an emergency.

> KryzIO does not replace official emergency services. The state warning system (RCB, 112) always takes precedence — KryzIO is a complement and a communication aid.

Built during **HackYeah 2026** — open task **SMART CITY**.

**Live demo:** https://kryzio.goveris.pl

## Features

- **Ask (chat)** — questions in plain Polish, e.g. "Czy na Kazimierzu grozi powódź?". The agent finds the place (or uses the device location), pulls current data and answers with the situation plus steps *before / during / after*, each with its source and update time. When the answer names the nearest shelter, it comes with a "Nawiguj w Google Maps" walking-directions link.
- **Life-threatening situations** — a sticky "Dzwoń 112" banner and steps taken straight from the official safety guide; emergency numbers are always visible.
- **Map** — summary tiles (warnings, water levels, air quality, power outages), a Leaflet map of Kraków with outages and shelters, the nearest shelter with walking directions.
- **Demo** — simulated flood, power outage and bomb threat scenarios for presentations, clearly marked with a SIMULATION banner (presentation instance only).
- **Honest about data** — stale readings are labelled with their age, missing data is reported as "Brak danych" instead of guessed, places outside Kraków and off-topic questions are politely refused.
- **Readable** — 18 px base font, WCAG 2.1 AA contrast, works from 360 px wide.

## Architecture

```
Browser ──HTTPS──▶ nginx (reverse proxy, TLS)
                    ├── /         ▶ frontend  static Vite build (nginx)
                    ├── /api/*    ▶ api       FastAPI ──▶ db (PostgreSQL 16)
                    └── /agent/*  ▶ agent     FastAPI + GLM 5.3 ──▶ api
                                   celery-worker / celery-beat ──▶ public sources ──▶ db
```

| Container | Stack | Role |
|-----------|-------|------|
| `frontend` | React 19 + Vite + TypeScript + Tailwind, Leaflet + OpenStreetMap | Chat, map and demo tabs |
| `api` | Python 3.12 + FastAPI | Read-only data endpoints, geocoding, safety guide, shelters, demo scenarios |
| `celery-worker`, `celery-beat` | Celery + Redis | Fetch every source on start, then refresh it on a schedule |
| `agent` | Python 3.12 + FastAPI, GLM 5.3 with tool calling | Conversational agent; `api` is its only data source |
| `db` | PostgreSQL 16 | Cached source readings, shelters, Kraków boundary |
| `redis` | Redis 7 | Celery broker |

The agent never reaches external sources itself: it calls `api` tools (`geocode`, warnings, water levels, air quality, outages, nearest shelter, guide) and builds the answer only from their results. The disclaimer about emergency services is appended by code, not by the model. Conversations live only in memory for the session (no chat logs).

API contract: [`docs_ai/api-contract.md`](docs_ai/api-contract.md). Planning documents (idea, PRD, spec, tasks): [`docs_ai/`](docs_ai/).

## Getting started

Requirements: Docker with Compose v2, Make.

```bash
make up          # builds and starts all containers (needs .env, see below)
make test        # api + agent (pytest) and frontend (vitest)
make lint        # ruff + oxlint
make down
```

Create `.env` in the repo root before the first `make up`:

```dotenv
GLM_API_KEY=
API_INTERNAL_TOKEN=
POSTGRES_USER=kryzio
POSTGRES_PASSWORD=
POSTGRES_DB=kryzio
DATABASE_URL=postgresql://kryzio:<POSTGRES_PASSWORD>@db:5432/kryzio
```

`API_INTERNAL_TOKEN` is a random string shared by `api` and `agent`. Everything else has a default in `api/app/config.py`, `agent/app/config.py` and `frontend/src/config/env.ts`; override it in `.env` when needed, e.g. `AIRLY_API_KEY` for Airly readings, `GLM_MODEL` / `GLM_BASE_URL` for the LLM, or the `DEMO_*` and `VITE_DEMO_*` variables for demo mode. The default `GLM_BASE_URL` targets the GLM Coding Plan endpoint; pay-as-you-go keys use `https://api.z.ai/api/paas/v4/`.

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| API | http://localhost:8000/health |
| Agent | http://localhost:8001/health |
| Agent API docs (try `POST /chat`) | http://localhost:8001/docs |
| API docs | http://localhost:8000/docs |

The Celery worker fetches all sources as soon as it starts (Kraków boundary first, shelters take about 40 s), so the tiles fill up a minute after `make up`. `make seed` runs the same fetch synchronously when you want to force it; `make celery-logs` shows the refresh runs.

The database schema (`db/init/`) is applied only when the `pgdata` volume is created. If you started the stack before a schema file existed, apply the missing files once:

```bash
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /docker-entrypoint-initdb.d/01-schema.sql'
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /docker-entrypoint-initdb.d/02-air-quality.sql'
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /docker-entrypoint-initdb.d/03-outage-streets.sql'
```

### Demo mode

The Demo tab is visible only with `VITE_DEMO_MODE=true` and is meant for presentations. The `api` needs `DEMO_MODE=true` and a random `DEMO_ADMIN_TOKEN`, sent as `X-Demo-Token` to switch scenarios; the frontend reads it from `VITE_DEMO_TOKEN`, which ends up in the public bundle, so use demo mode only on a presentation instance. An active scenario switches back to real data after `DEMO_TTL_MINUTES`. Shelters and the safety guide always stay real.

## Deployment

Production runs on a VPS with Docker Compose behind an nginx reverse proxy that terminates TLS. [`deploy/docker-compose.prod.yml`](deploy/docker-compose.prod.yml) has no published ports, no bind mounts or `--reload`, `restart: unless-stopped` and the static frontend from [`frontend/Dockerfile.prod`](frontend/Dockerfile.prod).

The proxy config lives on the server, outside the repo. It routes `/api/` and `/agent/` to the services with the prefix stripped, sets HSTS, logs paths without the query string and overwrites `X-Forwarded-For` with the client address.

```bash
cp deploy/docker-compose.prod.yml docker-compose.prod.yml   # the root copy is ignored by git
# .env: as in Getting started, plus APP_ENV=production, CORS_ORIGINS and public VITE_API_URL / VITE_AGENT_URL
docker compose -f docker-compose.prod.yml up -d --build
```

Things that matter in production:

- `VITE_*` values are baked into the bundle at build time — rebuild `frontend` after changing them.
- `APP_ENV=production` hides the API docs and skips the test run in the `api` entrypoint.
- `FORWARDED_ALLOW_IPS` lets `api` and `agent` see the real client IP from the proxy; without it every user shares one chat and geocoding rate limit.
- The page's security headers (`frame-ancestors`, `X-Frame-Options`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`) are set by the frontend image; the Content-Security-Policy is a `<meta>` tag generated at build time ([`frontend/csp.ts`](frontend/csp.ts)).
- Use an alphanumeric `POSTGRES_PASSWORD` (it is embedded in `DATABASE_URL`); PostgreSQL reads it only when the volume is first created.

## Data sources

| Source | Used for | Refresh | Terms |
|--------|----------|---------|-------|
| [IMGW-PIB public data](https://danepubliczne.imgw.pl/) | Meteorological and hydrological warnings, water levels | every 45 min | Public data; source: IMGW-PIB |
| [Tauron Dystrybucja](https://www.tauron-dystrybucja.pl/wylaczenia) | Planned and unplanned power outages | every 30 min | Publicly available outage list |
| [Punkty schronienia (KG PSP, dane.gov.pl)](https://dane.gov.pl) | Shelters and protective places | every 2 h | Open data, dane.gov.pl |
| [GIOŚ air quality API](https://powietrze.gios.gov.pl/) | Air quality index, PM2.5, PM10 | every 1 h | Public data; source: GIOŚ |
| [Airly](https://airly.org/) | Air quality (only when `AIRLY_API_KEY` is set) | every 2 h (rate limit) | Airly API terms |
| [Poradnik bezpieczeństwa 1/2025](https://www.gov.pl/web/poradnikbezpieczenstwa) (MON, MSWiA, RCB) | Before / during / after steps in `api/data/guide/` | static | Official document |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) via [Nominatim](https://nominatim.org/) | Map tiles, geocoding, Kraków boundary | boundary weekly, geocoding cached 1 h in memory | © OpenStreetMap contributors, ODbL; Nominatim usage policy (max 1 req/s) |

The safety guide covers flood, power outage, air attack and shelters, fire and general preparedness. It has no chapter on drought or air quality, so for those topics the agent answers "Brak danych" instead of inventing advice.

## Security and privacy

- No accounts and no stored conversations; chat sessions expire from memory (`SESSION_TTL_SECONDS`).
- Coordinates and addresses are stripped from access logs.
- Per-IP rate limits on chat and geocoding cap LLM costs and abuse; the agent skips the geocoding limit with `API_INTERNAL_TOKEN`.
- The agent is hardened against prompt injection: tool results are treated as data, texts are truncated, the model returns structured JSON validated by code.
- Accessibility (WCAG 2.1) and security audits were run before release; findings and fixes are recorded in [`docs_ai/07-tasks.md`](docs_ai/07-tasks.md).

## Use of AI and external resources

Disclosed per HackYeah rules:

- GLM 5.3 (Z.ai) — LLM powering the agent
- Claude Code — used for planning, documentation and coding assistance
- Public data and maps listed in [Data sources](#data-sources)

## Team

- Team Leader: Małgorzata Kapusta
- Team: Arkadiusz Sarach, Dawid Kapusta
