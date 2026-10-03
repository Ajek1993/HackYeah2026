# SPEC.md — KryzIO

> Tryb uproszczony: Commands + Boundaries (+ skrócona struktura i zasady git)

## Commands

| Operacja | Komenda |
|----------|---------|
| Start całości (4 kontenery) | `make up` (→ `docker compose up -d --build`) |
| Stop | `make down` |
| Logi | `make logs` |
| Testy — wszystko | `make test` |
| Testy — api | `make test-api` (→ `pytest` w kontenerze `api`) |
| Testy — agent | `make test-agent` (→ `pytest` w kontenerze `agent`) |
| Testy — frontend | `make test-frontend` (→ `vitest run`) |
| Lint | `make lint` (→ `ruff check` dla Pythona, `eslint` dla frontendu) |
| Format | `make format` (→ `ruff format`, `prettier`) |
| Seed schronów | `make seed` (ładuje `api/data/shelters.json` do `db`) |
| Frontend dev bez Dockera | `cd frontend && npm install && npm run dev` |
| Build frontendu (Vercel) | `cd frontend && npm run build` |

**Wymagania:** Docker + Docker Compose v2, Make, Python 3.12, Node 22 LTS, PostgreSQL 16 (obraz)

**Zmienne środowiskowe** (`.env`, minimalny zestaw w README): `GLM_API_KEY`, `GLM_MODEL`, `AIRLY_API_KEY`, `DATABASE_URL`, `API_URL`, `AGENT_URL`, `CORS_ORIGINS`, `DEMO_MODE`, `VITE_API_URL`, `VITE_AGENT_URL`, `VITE_DEMO_MODE`

## Struktura (skrót)

```
/
├── frontend/          — React + Vite + TS + Tailwind (zakładki: Czat, Mapa, Demo)
├── api/               — FastAPI: źródła danych, harmonogram, cache, schrony, demo
│   ├── app/sources/   — po jednym module na źródło (imgw, tauron, gios, airly, guide)
│   ├── app/demo/      — scenariusze symulowane (flood, power_outage, bomb_threat)
│   ├── data/          — shelters.json, poradnik (pliki tekstowe)
│   └── tests/
├── agent/             — FastAPI: agent GLM 5.3 + narzędzia wołające api
│   └── tests/
├── docker-compose.yml
├── Makefile
└── README.md
```

- `agent` nie łączy się z `db` ani źródłami zewnętrznymi — tylko przez HTTP do `api`
- `frontend` woła `agent` (czat) i `api` (mapa, panel)

## Git Workflow

- Commity i pushe **tylko na wyraźną prośbę autora**, przez skill `/commitandpush`
- Format: Conventional Commits po angielsku (`feat(agent): ...`)
- **Bez** `Co-Authored-By` i innych oznaczeń AI w commitach
- Większe funkcje na osobnych branchach o krótkich nazwach (np. `add-agent`, `add-map`)
- Pierwszy commit (szkielet repo) od razu — autor zatwierdza szkic przed wysłaniem
- Wersje i narzędzia zaakceptowane: Python 3.12, Node 22 LTS, PostgreSQL 16, ruff, eslint + prettier

## Boundaries

### Always (rób zawsze, bez pytania)

- Po każdej zmianie uruchom odpowiednie testy (`make test-*`) i lint
- Każda odpowiedź agenta oparta na danych z narzędzi musi zawierać źródło i czas aktualizacji
- Każda odpowiedź merytoryczna agenta kończy się dopiskiem o nadrzędności służb (RCB, 112)
- Brak danych → agent odpowiada „Brak danych”; dane > 3h → oznaczenie „dane sprzed X godz.”
- Adres poza Krakowem → „KryzIO działa na razie tylko na terenie Krakowa”
- Zagrożenie życia → baner „Dzwoń 112” (LLM + fallback słów kluczowych na froncie)
- Nowe zmienne środowiskowe dostają domyślną wartość w `config`; wymagane dopisuj do sekcji `.env` w README (bez wartości sekretów)
- Kod, komentarze, nazwy, commity po angielsku; UI po polsku
- Czcionka bazowa min. 18px, kontrast WCAG AA
- Źródła danych i zewnętrzne API dopisuj do README (wymóg ujawnienia HackYeah)

### Ask First (zatrzymaj się i zapytaj)

- Dodanie nowej zależności (pip / npm) spoza ustalonego stacku
- Dodanie nowego źródła danych albo zmiana częstotliwości odpytywania (rate limity)
- Zmiana schematu bazy lub kontraktu API między kontenerami
- Zmiana modelu LLM, system promptu agenta w zakresie zasad bezpieczeństwa lub limitów tokenów
- Dodanie piątego kontenera / zmiana docker-compose poza ustaloną architekturą
- Każda funkcja z „Out of scope” w PRD
- Zmiana treści dopisku prawnego lub komunikatów stałych (zasięg, „Brak danych”, 112)
- Commit, push, zmiana branchy

### Never (twarde zakazy)

- Nigdy nie commituj sekretów (klucze GLM, Airly, hasła DB) — tylko `.env`, który jest w `.gitignore`
- Nigdy nie loguj ani nie zapisuj adresów użytkowników i treści rozmów (także w testach i fixtures — tylko dane fikcyjne)
- Nigdy nie commituj przykładowych rozmów z prawdziwymi danymi osobowymi
- Nigdy nie pozwalaj agentowi podawać danych, których nie zwróciło narzędzie (żadnych „przewidywań” zalania z głowy modelu)
- Nigdy nie przedstawiaj KryzIO jako zastępstwa systemu państwowego (RCB, 112)
- Nigdy nie włączaj trybu Demo domyślnie (`DEMO_MODE` domyślnie `false` w `api/app/config.py`); dane symulowane zawsze oznaczone SYMULACJA
- Nigdy nie przekraczaj rate limitów źródeł (Airly co 2h, pozostałe co 30 min)
- Nigdy nie dodawaj `Co-Authored-By` ani oznaczeń Claude Code w git
- Nigdy nie commituj ani nie pushuj automatycznie bez prośby autora
- Nigdy nie przedstawiaj kodu sprzed hackathonu jako pracy z HackYeah
