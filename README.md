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

The Demo tab (simulated scenarios) is visible only with `VITE_DEMO_MODE=true` and is meant for presentations only.

## Data sources

- IMGW — meteorological and hydrological warnings, water levels
- Tauron Dystrybucja — planned and unplanned power outages
- GIOŚ — air quality
- Airly — air quality (cached, refreshed every 2h due to rate limits)
- Government safety guide (Poradnik bezpieczeństwa)
- Shelters in Kraków — source to be documented
- OpenStreetMap / Nominatim — maps and geocoding

## Use of AI and external resources

Disclosed per HackYeah rules:

- GLM 5.3 — LLM powering the agent
- Claude Code — used for planning, documentation and coding assistance

## Team

- _TBD_
