# 07 — Taski

> KryzIO · tryb uproszczony · taski w fazach, szczegóły dopisywane w trakcie
> Właściciele: **[A]** autor (frontend + agent) · **[B]** backend (api, dane, db, VPS) · **[P]** pomysł i prezentacja
> Statusy: `todo` · `in_progress` · `review` · `done`

## Faza 0 — Fundament (wspólna, odblokowuje pracę równoległą)

### T01 — Szkielet repo · `done` · [A]
- README, `.gitignore`, `.env.example`, `docs_ai/` z artefaktami PAF (PRD, SPEC)
- **Gotowe gdy:** pierwszy commit zatwierdzony przez autora i wypchnięty

### T02 — Kontrakt API `api` ↔ `agent` / `frontend` · `done` · [A]+[B]
- Spisać w `docs_ai/api-contract.md` endpointy i kształt JSON (bez implementacji): `GET /health`, `GET /warnings?lat&lon`, `GET /water-levels`, `GET /air-quality?lat&lon`, `GET /power-outages?lat&lon`, `GET /shelters/nearest?lat&lon`, `GET /shelters`, `GET /guide/{topic}`, `GET /geocode?q`, `GET /summary`, `GET /demo/scenarios`, `POST /demo/activate/{id}`
- Każdy odczyt danych zwraca `source`, `updated_at`, `is_stale`, `is_simulated`
- **Gotowe gdy:** obie strony zaakceptowały plik; agent i front mogą mockować odpowiedzi

### T03 — docker-compose + Makefile + szkielety kontenerów · `done` · [B → zrobione przez Claude na prośbę autora]
- 4 serwisy: `frontend`, `api`, `agent`, `db` (PostgreSQL 16); `api` i `agent` z `GET /health`
- Makefile: `up`, `down`, `logs`, `test`, `test-api`, `test-agent`, `test-frontend`, `lint`, `format`, `seed`
- Po jednym przykładowym teście w `api/tests`, `agent/tests`, `frontend`
- **Gotowe gdy:** `make up` stawia 4 kontenery, `curl localhost:8000/health` i `:8001/health` → 200, `make test` i `make lint` przechodzą

### T04 — Szkielet frontendu · `done` · [A]
- Vite + React + TS + Tailwind; zakładki **Czat** (start), **Mapa**, **Demo** (tylko gdy `VITE_DEMO_MODE=true`)
- Motyw: czcionka bazowa 18px, kontrast WCAG AA; stopka z numerami alarmowymi (F13)
- Design przez skill `frontend-design`
- **Gotowe gdy:** `npm run dev` pokazuje 3 zakładki (Demo ukryte przy fladze false), test vitest na ukrywanie Demo przechodzi

## Faza 1 — Dane (backend)

### T05 — Model danych i cache w `db` · `todo` · [B]
- Tabele: odczyty źródeł (`source`, `kind`, `payload`, `fetched_at`), schrony
- **Gotowe gdy:** migracja/inicjalizacja przy starcie, test zapisu i odczytu ostatniego odczytu

### T06 — Schrony: JSON + seed + najbliższy schron · `todo` · [B]
- `api/data/shelters.json` z realnego źródła (źródło w README), `make seed`, `GET /shelters`, `GET /shelters/nearest`
- **Gotowe gdy:** test: dla współrzędnych na Dębnikach zwraca najbliższy schron z odległością

### T07 — Geokodowanie + walidacja Krakowa · `todo` · [B]
- `GET /geocode?q=` przez Nominatim (z User-Agent i limitem zapytań), flaga `in_krakow`
- **Gotowe gdy:** testy: „Kobierzyńska, Kraków” → `in_krakow=true`; „Skawina” → `false`

### T08 — Źródło IMGW (ostrzeżenia + stany wód) · `todo` · [B]
- Moduł `api/app/sources/imgw.py`, zapis do cache
- **Gotowe gdy:** `GET /warnings` i `GET /water-levels` zwracają dane z `source` i `updated_at`; test na zapisanym fixture

### T09 — Źródło Tauron (wyłączenia prądu) · `todo` · [B]
- Scraping/API Tauron Dystrybucja dla Krakowa
- **Gotowe gdy:** `GET /power-outages` zwraca listę z lokalizacją; test na fixture

### T10 — Jakość powietrza GIOŚ + Airly · `todo` · [B]
- Oba źródła; przy konflikcie zwracany najświeższy odczyt (US-04)
- **Gotowe gdy:** `GET /air-quality` zwraca jeden odczyt z `source`; test konfliktu źródeł

### T11 — Harmonogram odświeżania + nieaktualność · `todo` · [B]
- Zadanie w tle: Airly co 2h, pozostałe co 30 min; błąd źródła → zostaje ostatni cache
- `is_stale=true` dla danych starszych niż 3h; brak cache → odpowiedź „brak danych”
- **Gotowe gdy:** testy: stale > 3h, błąd źródła nie kasuje cache, Airly nie częściej niż co 2h

### T12 — Poradnik bezpieczeństwa · `todo` · [B]
- Fragmenty poradnika jako pliki w `api/data/guide/` (powódź, brak prądu, atak / ukrycie, pożar, susza, jakość powietrza, ogólne), `GET /guide/{topic}`
- **Gotowe gdy:** każdy temat zwraca tekst ze źródłem

### T13 — `GET /summary` dla panelu · `todo` · [B]
- Zbiorcze podsumowanie zagrożeń w Krakowie (kafelki panelu)
- **Gotowe gdy:** jeden request zwraca stan wszystkich źródeł z `updated_at` i `is_stale`

## Faza 2 — Agent (autor; równolegle z fazą 1 na mockach z T02)

### T14 — Klient GLM 5.3 + system prompt · `done` · [A]
- Klient z tool calling, limit tokenów w konfiguracji; system prompt: tylko dane z narzędzi, „Brak danych”, sekcje sytuacja / przed / w trakcie / po, dopisek o służbach, off-topic maks. 2 zdania, tylko Kraków, po polsku
- **Gotowe gdy:** test z zamockowanym GLM sprawdza obecność zasad w prompcie i limit tokenów

### T15 — Narzędzia agenta · `done` · [A]
- `geocode`, `get_warnings`, `get_water_levels`, `get_air_quality`, `get_power_outages`, `find_nearest_shelter`, `get_guide` — wołają `api`
- **Gotowe gdy:** testy narzędzi na zamockowanym `api` (w tym `is_stale`, brak danych)

### T16 — Endpoint czatu z pamięcią sesji · `done` · [A]
- `POST /chat` z `session_id`; kontekst (adres, skład gospodarstwa) w pamięci procesu z TTL, bez zapisu do db i logów
- Odpowiedź strukturalna: `answer`, `sources[]`, `emergency` (bool), `out_of_area` (bool)
- **Gotowe gdy:** test: drugie pytanie w sesji korzysta z adresu z pierwszego; brak logowania treści

### T17 — Reguły specjalne · `done` · [A]
- Adres poza Krakowem → stały komunikat zasięgu; zagrożenie życia → `emergency=true`; błąd/timeout GLM → komunikat „Agent chwilowo niedostępny”
- **Gotowe gdy:** testy dla wszystkich trzech przypadków

## Faza 3 — Frontend (autor)

### T18 — Czat · `review` · [A]
- Okno czatu, wskaźnik „agent pisze…”, źródła z godziną pod odpowiedzią, oznaczenie „dane sprzed X godz.”, dopisek o służbach, `session_id` w `sessionStorage`
- **Gotowe gdy:** pytanie o Kobierzyńską zwraca odpowiedź ze źródłami end-to-end

### T19 — Szybkie pytania + baner 112 · `todo` · [A]
- Przyciski szybkich pytań (F6); baner „Dzwoń 112” z `tel:112` przy `emergency=true` **lub** słowach kluczowych (fallback)
- **Gotowe gdy:** test vitest: fallback słów kluczowych pokazuje baner bez odpowiedzi agenta

### T20 — Zakładka Mapa · `todo` · [A]
- Kafelki z `/summary`, mapa Leaflet + OSM, warstwy zagrożeń i schronów, wyszukiwanie adresu → marker + najbliższy schron z odległością
- **Gotowe gdy:** po wpisaniu adresu na mapie widać marker i najbliższy schron; nieaktualne kafelki oznaczone

## Faza 4 — Demo

### T21 — Scenariusze symulowane w `api` · `todo` · [B]
- `api/app/demo/`: powódź, brak prądu, atak bombowy; aktywny scenariusz podmienia odpowiedzi endpointów (`is_simulated=true`); endpointy demo → 404 gdy `DEMO_MODE=false`
- **Gotowe gdy:** testy: aktywacja scenariusza zmienia `/warnings`; przy fladze false → 404

### T22 — Zakładka Demo we froncie · `todo` · [A]
- Wybór scenariusza, stały baner SYMULACJA, czat i mapa na danych symulowanych, przełączenie resetuje czat
- **Gotowe gdy:** wszystkie 3 scenariusze przeklikane bez błędów; pytanie w scenariuszu ataku zwraca komunikat + poradnik + schron

## Faza 5 — Wdrożenie i wykończenie

### T23 — Deploy backendu na VPS · `todo` · [B]
- docker-compose na VPS, reverse proxy z HTTPS, CORS na domenę Vercela
- **Gotowe gdy:** `https://<domena>/health` → 200 z przeglądarki

### T24 — Deploy frontendu na Vercel · `todo` · [A]
- Zmienne `VITE_*` wskazują na VPS; wersja prezentacyjna z `VITE_DEMO_MODE=true`
- **Gotowe gdy:** publiczny link działa end-to-end (czat, mapa, demo)

### T25 — README końcowe · `todo` · [A]
- Uruchomienie, architektura, źródła danych z licencjami, ujawnienie AI/API/danych, zespół
- **Gotowe gdy:** nowa osoba uruchamia projekt z README przez `make up`

### T26 — Przegląd dostępności i bezpieczeństwa · `todo` · [A]
- Skill `wcag_audit` (18px, kontrast AA, 360px); agent `security-auditor` (brak sekretów, brak logowania rozmów)
- **Gotowe gdy:** brak krytycznych uwag

## Faza 6 — Zgłoszenie (równolegle od fazy 1)

### T27 — Prezentacja PDF ≤ 10 slajdów · `todo` · [P]
- Problem, persona Marta, rozwiązanie, demo (zrzuty scenariuszy), architektura, źródła, KryzIO jako uzupełnienie RCB, dalszy rozwój (push, EN, głos)
- **Gotowe gdy:** PDF ≤ 10 slajdów gotowy

### T28 — Materiały zgłoszeniowe · `todo` · [P]
- Tytuł, nazwa zespołu, skład, opis projektu, link do repo i demo, zrzuty ekranu
- **Gotowe gdy:** wszystko wgrane na platformę przed 4.10, 23:00

## Notatki z realizacji

### Ustalenia przed startem (krok 8)
- Commity: tylko na prośbę autora, branch `main`
- Review: po każdej fazie
- Claude realizuje taski autora [A]; backend [B] robi kolega
- GLM: model `glm-5.3`, base URL `https://api.z.ai/api/coding/paas/v4/` (GLM Coding Plan — klucz autora nie działa na `/api/paas/v4/`: 429/1113 brak środków; zgodny z OpenAI SDK, tool calling wspierany)

### Faza 0 — postęp
- T02: szkic `docs_ai/api-contract.md` — czeka na akceptację backendu
- T04: `frontend/` — Vite 8 + React 19 + TS + Tailwind 4; zakładki Zapytaj / Mapa / Demo (flaga), pas alarmowy 112 + inne numery, czcionka 18px, Atkinson Hyperlegible Next; vitest 5/5, oxlint OK, build OK

- T03: `docker-compose.yml` (db Postgres 16, api :8000, agent :8001, frontend :5173), Dockerfile dla api/agent (Python 3.12) i frontend (Node 22), Makefile; `/health` api i agent → 200; pytest api 2/2, agent 1/1, vitest 5/5, ruff + oxlint OK; `seed` to stub do T06. Zweryfikowane komendami docker compose (make niezainstalowany)

### Faza 2 — postęp
- T14: `agent/app/llm.py` (`GLMClient`: OpenAI SDK, tool calling, `max_tokens`/`temperature`/`timeout` z konfiguracji, błędy → `LLMUnavailableError`), `agent/app/prompt.py` (system prompt + stałe komunikaty), nowe zmienne `GLM_MAX_TOKENS=1200`, `GLM_TEMPERATURE=0.2`, `GLM_TIMEOUT=30`; pytest agent 16/16, ruff OK; smoke test na żywym GLM OK (tool call `geocode`, komunikat zasięgu, off-topic 2 zdania, poprawny JSON; 4–10 s)
- T15: `agent/app/tools.py` — `TOOL_DEFINITIONS` (7 narzędzi, schematy function calling) + `ToolExecutor` (httpx → `api`); zwraca `ToolResult` (treść dla modelu, `sources[]` z envelope, `payload` dla reguł T17); błąd / brak `api` → „Brak danych” zamiast wyjątku; `data: null` → `note: "Brak danych"`; nieaktualne dane → `age_hours`; pytest agent 37/37, ruff OK; na żywym GLM model sam wybiera `geocode` dla miejsca i `get_guide` dla pytań poradnikowych
- T16: `POST /chat` + `DELETE /chat/{session_id}` (`agent/app/main.py`), `ChatService` (`agent/app/chat.py`: pętla tool calling z limitem `AGENT_MAX_TOOL_ROUNDS`, potem wymuszona odpowiedź bez narzędzi; parsowanie JSON z fallbackiem na tekst; `sources[]` z narzędzi, deduplikowane; `is_simulated` z dowolnego źródła), `SessionStore` (`agent/app/session.py`: pamięć procesu, TTL `SESSION_TTL_SECONDS`, limit `SESSION_MAX_MESSAGES`, tylko pytania i odpowiedzi — bez wyników narzędzi); pytest agent 56/56, ruff OK; e2e na żywym GLM: drugie pytanie korzysta z adresu z pierwszego, bez `api` → „Brak danych”; czas odpowiedzi 25–31 s

- Po review T16 (decyzje autora): thinking GLM wyłączony (`GLM_THINKING=disabled`, `extra_body`); rady tylko z poradnika — bez `get_guide` agent podaje „Brak danych” + 112 + RCB (poradnik podepniemy z T12); `disclaimer: null` dla off-topic i spoza Krakowa — zaakceptowane; prompt prosi o równoległe wywołania narzędzi; pytest agent 57/57
- T17: zasięg — `geocode` z `found: true, in_krakow: false` (i żadnym miejscem w Krakowie) przerywa pętlę bez kolejnej rundy GLM i zwraca stały komunikat (bez sekcji, źródeł, dopisku); flaga `out_of_area` od modelu też wymusza stały komunikat; zagrożenie życia — `emergency` od modelu (fallback słów kluczowych: front, T19); `LLMUnavailableError` → `503 {"error": "agent_unavailable", "message": "Agent chwilowo niedostępny"}`, pytanie nie trafia do sesji; fixture `make_client` przeniesiona do `tests/conftest.py`; pytest agent 66/66, ruff OK; na żywym GLM: „woda wlewa się do piwnicy…” → `emergency: true`, odpowiedź zaczyna się od „Dzwoń 112” (13 s)
- Po review T17 (decyzja autora: „sam poradnik, 112 + RCB”): prompt zakazuje własnych kroków także przy `emergency`; dodatkowo w kodzie — `emergency` bez danych z `get_guide` → stały komunikat `EMERGENCY_NO_GUIDE_MESSAGE` („Dzwoń 112. Brak danych z poradnika bezpieczeństwa — postępuj według poleceń służb i śledź komunikaty RCB.”), bo sam prompt łamany był w 2 na 3 próbach; pytest agent 69/69

- Faza 0 i faza 2 zaakceptowane przez autora (review po fazie) — T02–T04, T14–T17 `done`; kontrakt API (T02) zaakceptowany

- `make` zainstalowany (GNU Make 4.4.1, Chocolatey); `make test-agent` z Git Basha OK

### Faza 3 — postęp
- T18: `src/api/chat.ts` (klient `POST /chat` / `DELETE /chat/{id}`, typy z kontraktu), `src/hooks/useChat.ts` (wymiany pytanie–odpowiedź, retry, reset), `src/components/chat/` (`ExchangeView`, `ActionPlan` — przed / w trakcie / po jako trasa ewakuacyjna, `SourceList` — źródło + godzina + „dane sprzed X godz.”, `RichText` — minimalny Markdown bez `innerHTML`), `src/lib/time.ts` (czas Kraków); komunikat oczekiwania z `aria-live`, błąd 503 / brak sieci → komunikat + wskazówka 112 + „Spróbuj ponownie”; „Nowa rozmowa” czyści sesję w agencie; vitest 17/17, oxlint OK, build OK; brak zrzutów ekranu (rozszerzenie Chrome niepołączone)
- Hot reload frontendu w Dockerze na Windows nie działał (bind mount nie przekazuje zdarzeń plików) — `VITE_USE_POLLING=true` w `docker-compose.yml` + `server.watch.usePolling` w `vite.config.ts`

### Odstępstwa
- Lint frontendu: `oxlint` (domyślny w szablonie Vite) zamiast `eslint`
- Zakładka czatu nazwana „Zapytaj” (czytelniej niż „Czat”)
- T18: `session_id` w pamięci strony zamiast `sessionStorage` — PRD Story 1 wymaga, by odświeżenie strony czyściło kontekst (`sessionStorage` przetrwałby odświeżenie)
- T18: gdy agent zwraca `sections`, front pokazuje plan działania zamiast `answer` (treść się dubluje)
- T14: dopisek o służbach dokleja kod (`DISCLAIMER`), nie LLM — gwarancja obecności w każdej odpowiedzi; prompt zabrania go powtarzać i przedstawiać KryzIO jako zastępstwo służb
- T14: prompt po angielsku (zasada: kod po angielsku), stałe komunikaty i odpowiedzi po polsku; model zwraca JSON (`answer`, `sections`, `emergency`, `out_of_area`, `off_topic`), a `sources` w T16 zbierane będą z odpowiedzi narzędzi, nie od modelu

### Do decyzji autora
- Treść nowego stałego komunikatu `EMERGENCY_NO_GUIDE_MESSAGE` do akceptacji
- T16: czas odpowiedzi — każda runda GLM 4–9 s; przy działającym `api` typowo 3 rundy (geocode → dane równolegle → odpowiedź) ≈ 15 s; dalsze opcje: usunąć dublowanie `answer` + `sections` w JSON (mniej tokenów) albo streaming odpowiedzi

