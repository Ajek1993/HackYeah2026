# KryzIO

AI agent for Kraków residents that aggregates public crisis data (IMGW, Tauron, GIOŚ, Airly, safety guide, shelters) and tells you what to do at your address — before, during and after an emergency.

> KryzIO does not replace official emergency services. The state warning system (RCB, 112) always takes precedence — KryzIO is a complement and a communication aid.

Built during **HackYeah 2026** — open task **SMART CITY**.

## Status

Work in progress — repository skeleton. Planning documents live in [`docs_ai/`](docs_ai/).

## Architecture (planned)

| Container | Stack | Role |
|-----------|-------|------|
| `frontend` | React + Vite + TypeScript + Tailwind, Leaflet + OpenStreetMap | Chat, map, demo tab |
| `api` | Python 3.12 + FastAPI | Data sources, scheduled refresh, cache, shelters, demo scenarios |
| `agent` | Python 3.12 + FastAPI, GLM 5.3 (tool calling) | Conversational agent using `api` as its only data source |
| `db` | PostgreSQL 16 | Cache of source readings, shelters |

Deployment: `frontend` on Vercel, `api` + `agent` + `db` via Docker Compose on a VPS.

## Getting started

Requirements: Docker with Compose v2, Make.

```bash
make up          # creates .env from .env.example if missing, builds and starts all containers
make test        # api + agent (pytest) and frontend (vitest)
make lint        # ruff + oxlint
make down
```

Fill in `GLM_API_KEY` and `AIRLY_API_KEY` in `.env`. The default `GLM_BASE_URL` targets the GLM Coding Plan endpoint; pay-as-you-go keys use `https://api.z.ai/api/paas/v4/`.

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| API | http://localhost:8000/health |
| Agent | http://localhost:8001/health |
| Agent API docs (try `POST /chat`) | http://localhost:8001/docs |
| API docs | http://localhost:8000/docs |

The database schema (`db/init/`) is applied only when the `pgdata` volume is created. If you started the stack before a schema file existed, apply the missing files once:

```bash
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /docker-entrypoint-initdb.d/01-schema.sql'
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /docker-entrypoint-initdb.d/02-air-quality.sql'
```

Load the data right after the first start (Kraków boundary, shelters, Tauron, IMGW, GIOŚ); afterwards Celery beat refreshes it on its own:

```bash
make seed
```

The Demo tab (simulated scenarios) is visible only with `VITE_DEMO_MODE=true` and is meant for presentations only.

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

## Use of AI and external resources

Disclosed per HackYeah rules:

- GLM 5.3 — LLM powering the agent
- Claude Code — used for planning, documentation and coding assistance

## Team

- Team Leader: Małgorzata Kapusta 
- Team: Arkadiusz Sarach, Dawid Kapusta
