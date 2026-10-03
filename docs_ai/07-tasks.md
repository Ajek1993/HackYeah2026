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

### T05 — Model danych i cache w `db` · `done` · [B]
- Tabele: odczyty źródeł (`source`, `kind`, `payload`, `fetched_at`), schrony
- **Gotowe gdy:** migracja/inicjalizacja przy starcie, test zapisu i odczytu ostatniego odczytu

### T06 — Schrony: JSON + seed + najbliższy schron · `done` · [B]
- `api/data/shelters.json` z realnego źródła (źródło w README), `make seed`, `GET /shelters`, `GET /shelters/nearest`
- **Gotowe gdy:** test: dla współrzędnych na Dębnikach zwraca najbliższy schron z odległością

### T07 — Geokodowanie + walidacja Krakowa · `done` · [B]
- `GET /geocode?q=` przez Nominatim (z User-Agent i limitem zapytań), flaga `in_krakow`
- **Gotowe gdy:** testy: „Kobierzyńska, Kraków” → `in_krakow=true`; „Skawina” → `false`

### T08 — Źródło IMGW (ostrzeżenia + stany wód) · `done` · [B]
- Moduł `api/app/sources/imgw.py`, zapis do cache
- **Gotowe gdy:** `GET /warnings` i `GET /water-levels` zwracają dane z `source` i `updated_at`; test na zapisanym fixture

### T09 — Źródło Tauron (wyłączenia prądu) · `done` · [B]
- Scraping/API Tauron Dystrybucja dla Krakowa
- **Gotowe gdy:** `GET /power-outages` zwraca listę z lokalizacją; test na fixture

### T10 — Jakość powietrza GIOŚ + Airly · `done` · [B]
- Oba źródła; przy konflikcie zwracany najświeższy odczyt (US-04)
- **Gotowe gdy:** `GET /air-quality` zwraca jeden odczyt z `source`; test konfliktu źródeł

### T11 — Harmonogram odświeżania + nieaktualność · `done` · [B]
- Zadanie w tle: Airly co 2h, pozostałe co 30 min; błąd źródła → zostaje ostatni cache
- `is_stale=true` dla danych starszych niż 3h; brak cache → odpowiedź „brak danych”
- **Gotowe gdy:** testy: stale > 3h, błąd źródła nie kasuje cache, Airly nie częściej niż co 2h

### T12 — Poradnik bezpieczeństwa · `done` · [B]
- Fragmenty poradnika jako pliki w `api/data/guide/` (powódź, brak prądu, atak / ukrycie, pożar, susza, jakość powietrza, ogólne), `GET /guide/{topic}`
- **Gotowe gdy:** każdy temat zwraca tekst ze źródłem

### T13 — `GET /summary` dla panelu · `done` · [B]
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

### T18 — Czat · `done` · [A]
- Okno czatu, wskaźnik „agent pisze…”, źródła z godziną pod odpowiedzią, oznaczenie „dane sprzed X godz.”, dopisek o służbach, `session_id` w `sessionStorage`
- **Gotowe gdy:** pytanie o Kobierzyńską zwraca odpowiedź ze źródłami end-to-end

### T19 — Szybkie pytania + baner 112 · `done` · [A]
- Przyciski szybkich pytań (F6); baner „Dzwoń 112” z `tel:112` przy `emergency=true` **lub** słowach kluczowych (fallback)
- **Gotowe gdy:** test vitest: fallback słów kluczowych pokazuje baner bez odpowiedzi agenta

### T20 — Zakładka Mapa · `done` · [A]
- Kafelki z `/summary`, mapa Leaflet + OSM, warstwy zagrożeń i schronów, wyszukiwanie adresu → marker + najbliższy schron z odległością
- **Gotowe gdy:** po wpisaniu adresu na mapie widać marker i najbliższy schron; nieaktualne kafelki oznaczone

### T29 — Lokalizacja urządzenia · `done` · [A] (+ [B]: `GET /reverse`)
- Uwaga autora: gdy w pytaniu nie ma adresu, aplikacja korzysta z lokalizacji użytkownika
- Front pyta o zgodę przy pierwszym pytaniu; `location` w `POST /chat`; przycisk „Użyj mojej lokalizacji” w Mapie
- Agent: narzędzie `reverse_geocode`, notatka systemowa z lokalizacją (nie w sesji), reguła zasięgu jak dla adresu
- `api`: `GET /reverse?lat&lon` (Nominatim reverse, kształt jak `/geocode`) — do zrobienia przez backend
- **Gotowe gdy:** pytanie bez adresu przy udzielonej zgodzie zwraca odpowiedź dla okolicy użytkownika; odmowa nie blokuje czatu

## Faza 4 — Demo

### T21 — Scenariusze symulowane w `api` · `done` · [B → zrobione przez Claude na prośbę autora]
- `api/app/demo/`: powódź, brak prądu, atak bombowy; aktywny scenariusz podmienia odpowiedzi endpointów (`is_simulated=true`); endpointy demo → 404 gdy `DEMO_MODE=false`
- X5: przełączanie wymaga `X-Demo-Token` (`DEMO_ADMIN_TOKEN`), scenariusz wygasa po `DEMO_TTL_MINUTES`; schrony i poradnik zostają prawdziwe
- **Gotowe gdy:** testy: aktywacja scenariusza zmienia `/warnings`; przy fladze false → 404

### T22 — Zakładka Demo we froncie · `done` · [A]
- Wybór scenariusza, stały baner SYMULACJA, czat i mapa na danych symulowanych, przełączenie resetuje czat
- Baner na każdej zakładce (taśma ostrzegawcza, godzina wygaśnięcia, „Zakończ symulację”); pytania podpowiedzi per scenariusz; `VITE_DEMO_TOKEN` = `DEMO_ADMIN_TOKEN`
- Agent: zawsze pobiera ostrzeżenia przy odpowiedzi o miejsce (inaczej pomijał symulowany alarm, gdy użytkownik sam pisał „ogłoszono alarm”)
- **Gotowe gdy:** wszystkie 3 scenariusze przeklikane bez błędów; pytanie w scenariuszu ataku zwraca komunikat + poradnik + schron

## Faza 5 — Wdrożenie i wykończenie

### T23 — Deploy backendu na VPS · `done` · [B]
- Decyzja autora: rezygnujemy z Vercela, całość (frontend, api, agent, db) na VPS
- docker-compose na VPS, reverse proxy z HTTPS, CORS na domenę aplikacji
- Z audytu bezpieczeństwa (infrastruktura, odłożone przez autora):
  - N1: `docker-compose.prod.yml` — sieci `edge` / `backend (internal)`, porty tylko na proxy, bez bind mountów i `--reload`, `restart`, healthchecki, `USER` w obrazach Python, hasło Redis
  - N2/N3: proxy z TLS 1.2/1.3, `server_tokens off`, nagłówki bezpieczeństwa, limity body i timeouty, `proxy_set_header` + uvicorn `--proxy-headers --forwarded-allow-ips` (inaczej limiter widzi IP proxy), access log z `$uri` zamiast `$request_uri`
  - D3: role DB (scraper zapis, api tylko odczyt), agent bez zmiennych DB
  - D4: osobne pliki env na usługę, hasła przez `secrets:`, `statement_timeout` i `idle_in_transaction_session_timeout`
  - X2: testy poza entrypointem, obraz bez zależności dev; X3: lockfile z hashami i `pip-audit`
  - Na serwerze: `APP_ENV=production`, losowy `API_INTERNAL_TOKEN`, losowe hasło Postgresa, `DEMO_MODE=true` z losowym `DEMO_ADMIN_TOKEN` (instancja prezentacyjna)
- **Gotowe gdy:** `https://kryzio.goveris.pl/health` → 200 z przeglądarki

### T24 — Deploy frontendu na VPS · `done` · [A]
- Zamiast Vercela: statyczny build (`npm run build`) serwowany przez reverse proxy z T23, bez serwera deweloperskiego Vite
- Zmienne `VITE_*` wskazują publiczne adresy `api` i `agent` na VPS (wbudowywane przy buildzie); wersja prezentacyjna z `VITE_DEMO_MODE=true` i `VITE_DEMO_TOKEN`
- Z audytu (F4, N2): nagłówki w proxy (`frame-ancestors 'none'`, HSTS, `nosniff`, `Referrer-Policy`, `Permissions-Policy: geolocation=(self)`); CSP z `<meta>` (build) już jest
- **Gotowe gdy:** publiczny link działa end-to-end (czat, mapa, demo)

### T25 — README końcowe · `done` · [A]
- Uruchomienie, architektura, źródła danych z licencjami, ujawnienie AI/API/danych, zespół
- **Gotowe gdy:** nowa osoba uruchamia projekt z README przez `make up`

### T26 — Przegląd dostępności i bezpieczeństwa · `done` · [A]
- Skill `wcag_audit` (18px, kontrast AA, 360px); agent `security-auditor` (brak sekretów, brak logowania rozmów)
- **Gotowe gdy:** brak krytycznych uwag

## Faza 6 — Zgłoszenie (równolegle od fazy 1)

### T27 — Prezentacja PDF ≤ 10 slajdów · `done` · [P]
- Problem, persona Marta, rozwiązanie, demo (zrzuty scenariuszy), architektura, źródła, KryzIO jako uzupełnienie RCB, dalszy rozwój (push, EN, głos)
- **Gotowe gdy:** PDF ≤ 10 slajdów gotowy

### T28 — Materiały zgłoszeniowe · `done` · [P]
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
- T19: szybkie pytania wysyłane jednym kliknięciem; `EmergencyBanner` („Dzwoń 112”, `tel:112`, `role="alert"`) nad odpowiedzią przy `emergency: true` lub słowach kluczowych (`src/lib/emergency.ts`, bez polskich znaków i wielkości liter) — widoczny od razu po wysłaniu, także w trakcie czekania i przy 503; słowa kluczowe opisują sytuację „tu i teraz”, pytania o przygotowanie („jak się przygotować na pożar?”) banera nie włączają
- T20: `src/api/data.ts` (klient `api` wg kontraktu), `MapView` — kafelki z `/summary` (status słownie, nie tylko kolorem; „dane sprzed X godz.”; „Dane symulowane”), wyszukiwanie adresu (`/geocode` → poza Krakowem stały komunikat, nie znaleziono → prośba o doprecyzowanie) → `/shelters/nearest?limit=1` → karta schronu z odległością; `LeafletMap` (Leaflet 1.9.4 + kafelki OSM, bez `react-leaflet`): warstwy ostrzeżeń (GeoJSON), wyłączeń prądu i schronów z przełącznikami, schron jako znak obrony cywilnej, przerywana linia adres → najbliższy schron; vitest 41/41 (Leaflet zamockowany w testach), oxlint OK, build OK; brak zrzutów ekranu (rozszerzenie Chrome niepołączone); bez endpointów `api` mapa pokazuje „Brak danych”
- T29: decyzje autora — zgoda na lokalizację przy pierwszym pytaniu, zasięg przez nowy `GET /reverse` w `api`; kontrakt zaktualizowany (`/reverse`, pole `location`); agent: `reverse_geocode`, `build_location_note` (nazwane miejsce ma pierwszeństwo — na żywym GLM sprawdzone dla pytania bez adresu i z „Rynkiem Głównym”); front: `src/lib/geolocation.ts`, `useChat` (lokalizacja raz na stronę, tylko w pamięci), podpowiedź pod polem pytania, „Czekam na zgodę na lokalizację”, przycisk w Mapie; pytest agent 80/80, vitest 48/48, oxlint + build OK

- Faza 3 zaakceptowana przez autora — T18–T20 `done`; T29: część [A] (agent + front) zaakceptowana, task `in_progress` do czasu `GET /reverse` w `api` [B]

### Backend — endpointy `api` (branch `add-api-endpoints`, decyzja zespołu: robi autor/Claude)
- Scrapery kolegi (schrony, Tauron, IMGW, Celery beat, schemat PostGIS) + nowe w `api`:
  - `GET /shelters`, `/shelters/nearest` (KNN po indeksie, sortowanie w metrach), `/warnings`, `/water-levels`, `/power-outages`, `/air-quality`, `/geocode`, `/reverse`, `/guide/{topic}`, `/summary` wg kontraktu
  - granica Krakowa z OSM/Nominatim w `ref_areas` (powiat 1261) — filtr „w Krakowie” (`ST_Contains`, fallback bbox) i geometria ostrzeżeń meteo
  - GIOŚ (co 1h, 9 stacji, `db/init/02-air-quality.sql`), Airly tylko z kluczem (co 2h)
  - poradnik: `api/data/guide/*.json` wiernie z „Poradnika bezpieczeństwa” 1/2025 (gov.pl) — powódź, blackout, atak z powietrza + schronienia, pożar, ogólne; susza i jakość powietrza nie występują w poradniku → `data: null`
  - Nominatim: 1 req/s, User-Agent z kontaktem, cache tylko w pamięci; filtr access logu usuwa query string (adresy i współrzędne nie trafiają do logów — audyt X1)
  - czasy w odpowiedziach w strefie Kraków (`+02:00`)
- Zależności: `httpx`, `psycopg[pool]` (decyzja autora); async pool w lifespan FastAPI
- Weryfikacja: pytest api 185/185 (w tym testy integracyjne na PostGIS), agent 80/80, vitest 48/48; e2e na żywym GLM: Kobierzyńska → stany Wisły/Rudawy/Wilgi i ostrzeżenie o suszy z godziną + kroki z poradnika; Skawina → komunikat zasięgu (2,4 s); „najbliższy schron” z lokalizacją → 3 schrony z odległością
- Lint: na prośbę autora poprawione także starsze scrapery i ich testy (formatowanie, importy, `raise ... from exc` przy retry, dokładne wyjątki zamiast `pytest.raises(Exception)`); `make lint` przechodzi dla api, agent i frontend

- Review backendu (T06–T13) i T29 zaakceptowane przez autora — `done`; T26 `in_progress` (audyty WCAG i bezpieczeństwa gotowe, poprawki na branchu `add-api-endpoints`)

### T26 — poprawki po audytach (branch `add-api-endpoints`)
- WCAG (wszystkie 11 z `specs/wcag_repair_plan.md`): biały fokus na pasku 112 i banerze, lista tekstowa ostrzeżeń i wyłączeń pod mapą, landmark `main` + „Przejdź do treści”, pytanie jako `h2`, reflow paska alarmowego (`hidden`, przewijanie, `flex-wrap`, `static` przy niskim ekranie), polskie etykiety Leaflet, `aria-controls` tylko dla istniejących elementów, `aside` w Demo
- Agent: maks. 3 rundy i 6 wywołań na rundę, limit czasu 45 s, limit 5000 sesji; walidacja argumentów narzędzi (Pydantic + JSON Schema); dane z narzędzi oznaczone w prompcie jako niezaufane i obcinane do 500 znaków; lokalizacja dla modelu zaokrąglona do ~100 m (narzędzia dostają dokładną); `session_id` nadawany przez agenta; `extra="forbid"`; async (AsyncOpenAI, httpx.AsyncClient); limit 10 pytań/min na IP (429); docs wyłączone przy `APP_ENV=production`; ostrzejsza reguła „tylko kroki z poradnika” przy zagrożeniu życia
- api: limit 30 geokodowań/min na IP (agent z `X-Internal-Token` pominięty); docs wyłączone w produkcji; scrapery nie wygaszają danych przy podejrzanie małym lub pustym feedzie (< 50% aktywnych); jawne „brak ostrzeżeń” IMGW wygasza stare ostrzeżenia; współrzędne Tauronu walidowane przed WKT
- Frontend: font hostowany lokalnie (`@fontsource/atkinson-hyperlegible-next`, bez Google Fonts), CSP jako `<meta>` w buildzie (`csp.ts` z testami), linki źródeł tylko `https`, `session_id` z odpowiedzi agenta, komunikat przy 429
- Weryfikacja: pytest api 197/197, agent 109/109, vitest 59/59, `make lint` OK, build z CSP; na żywym GLM: nowe ID sesji, kontekst w drugim pytaniu, zmyślone ID zastąpione, najbliższy schron 145 m (dokładna lokalizacja), emergency z krokami z poradnika; limity 429 działają; brak adresów i współrzędnych w logach
- Infrastruktura z audytu przeniesiona do T23 / T24 (decyzja autora)
- Review autora: zaakceptowane — T26 `done`

### Odstępstwa
- Lint frontendu: `oxlint` (domyślny w szablonie Vite) zamiast `eslint`
- Zakładka czatu nazwana „Zapytaj” (czytelniej niż „Czat”)
- T18: `session_id` w pamięci strony zamiast `sessionStorage` — PRD Story 1 wymaga, by odświeżenie strony czyściło kontekst (`sessionStorage` przetrwałby odświeżenie)
- T18: gdy agent zwraca `sections`, front pokazuje plan działania zamiast `answer` (treść się dubluje)
- T14: dopisek o służbach dokleja kod (`DISCLAIMER`), nie LLM — gwarancja obecności w każdej odpowiedzi; prompt zabrania go powtarzać i przedstawiać KryzIO jako zastępstwo służb
- T14: prompt po angielsku (zasada: kod po angielsku), stałe komunikaty i odpowiedzi po polsku; model zwraca JSON (`answer`, `sections`, `emergency`, `out_of_area`, `off_topic`), a `sources` w T16 zbierane będą z odpowiedzi narzędzi, nie od modelu

### Do decyzji autora
- Treść nowego stałego komunikatu `EMERGENCY_NO_GUIDE_MESSAGE` do akceptacji
- Prywatność logów `api`: rozwiązane filtrem access logu (query string usuwany); logi przyszłego reverse proxy trzeba skonfigurować tak samo (`$uri` zamiast `$request_uri`)
- T20: nowa zależność `leaflet` + `@types/leaflet` (Leaflet był w ustalonym stacku architektury)
- Przy `emergency` z załadowanym poradnikiem model po zaostrzeniu promptu trzyma się poradnika, ale nadal potrafi dodać pojedyncze doprecyzowanie (np. „nie schodź do piwnicy, jeśli woda dotyka gniazdek”) — twarde wymuszenie wymagałoby składania odpowiedzi z kroków poradnika w kodzie
- T16: czas odpowiedzi — każda runda GLM 4–9 s; przy działającym `api` typowo 3 rundy (geocode → dane równolegle → odpowiedź) ≈ 15 s; dalsze opcje: usunąć dublowanie `answer` + `sections` w JSON (mniej tokenów) albo streaming odpowiedzi

### Po wdrożeniu (branch `prod-frontend-build`)
- Front na produkcji szedł przez serwer deweloperski Vite i bez nagłówków bezpieczeństwa: `frontend/Dockerfile.prod` (build + `nginx-unprivileged`, port 8080) z nagłówkami w `frontend/nginx/`
- `api` i `agent` za proxy widziały IP nginx, więc limit czatu był wspólny dla wszystkich: `FORWARDED_ALLOW_IPS` + proxy nadpisuje `X-Forwarded-For` adresem klienta
- Po redeployu z czystą bazą kafelki pokazywały „Brak danych” do ręcznego seeda: worker Celery pobiera wszystkie źródła przy starcie
- Wzorce dla VPS w `deploy/` (compose bez bind mountów i `--reload`, `restart`; config nginx z HSTS i logiem bez query stringa)
