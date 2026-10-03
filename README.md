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

_Coming soon_ — `make up`, `make test`.

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
