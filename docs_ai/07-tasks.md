# 07 — Taski

> KryzIO · tryb uproszczony · taski w fazach, szczegóły dopisywane w trakcie
> Właściciele: **[A]** autor (frontend + agent) · **[B]** backend (api, dane, db, VPS) · **[P]** pomysł i prezentacja
> Statusy: `todo` · `in_progress` · `review` · `done`

## Faza 0 — Fundament (wspólna, odblokowuje pracę równoległą)

### T01 — Szkielet repo · `done` · [A]
- README, `.gitignore`, `.env.example`, `docs_ai/` z artefaktami PAF (PRD, SPEC)
- **Gotowe gdy:** pierwszy commit zatwierdzony przez autora i wypchnięty

### T02 — Kontrakt API `api` ↔ `agent` / `frontend` · `review` · [A]+[B]
- Spisać w `docs_ai/api-contract.md` endpointy i kształt JSON (bez implementacji): `GET /health`, `GET /warnings?lat&lon`, `GET /water-levels`, `GET /air-quality?lat&lon`, `GET /power-outages?lat&lon`, `GET /shelters/nearest?lat&lon`, `GET /shelters`, `GET /guide/{topic}`, `GET /geocode?q`, `GET /summary`, `GET /demo/scenarios`, `POST /demo/activate/{id}`
- Każdy odczyt danych zwraca `source`, `updated_at`, `is_stale`, `is_simulated`
- **Gotowe gdy:** obie strony zaakceptowały plik; agent i front mogą mockować odpowiedzi

### T03 — docker-compose + Makefile + szkielety kontenerów · `review` · [B → zrobione przez Claude na prośbę autora]
- 4 serwisy: `frontend`, `api`, `agent`, `db` (PostgreSQL 16); `api` i `agent` z `GET /health`
- Makefile: `up`, `down`, `logs`, `test`, `test-api`, `test-agent`, `test-frontend`, `lint`, `format`, `seed`
- Po jednym przykładowym teście w `api/tests`, `agent/tests`, `frontend`
- **Gotowe gdy:** `make up` stawia 4 kontenery, `curl localhost:8000/health` i `:8001/health` → 200, `make test` i `make lint` przechodzą

### T04 — Szkielet frontendu · `review` · [A]
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

### T14 — Klient GLM 5.3 + system prompt · `todo` · [A]
- Klient z tool calling, limit tokenów w konfiguracji; system prompt: tylko dane z narzędzi, „Brak danych”, sekcje sytuacja / przed / w trakcie / po, dopisek o służbach, off-topic maks. 2 zdania, tylko Kraków, po polsku
- **Gotowe gdy:** test z zamockowanym GLM sprawdza obecność zasad w prompcie i limit tokenów

### T15 — Narzędzia agenta · `todo` · [A]
- `geocode`, `get_warnings`, `get_water_levels`, `get_air_quality`, `get_power_outages`, `find_nearest_shelter`, `get_guide` — wołają `api`
- **Gotowe gdy:** testy narzędzi na zamockowanym `api` (w tym `is_stale`, brak danych)

### T16 — Endpoint czatu z pamięcią sesji · `todo` · [A]
- `POST /chat` z `session_id`; kontekst (adres, skład gospodarstwa) w pamięci procesu z TTL, bez zapisu do db i logów
- Odpowiedź strukturalna: `answer`, `sources[]`, `emergency` (bool), `out_of_area` (bool)
- **Gotowe gdy:** test: drugie pytanie w sesji korzysta z adresu z pierwszego; brak logowania treści

### T17 — Reguły specjalne · `todo` · [A]
- Adres poza Krakowem → stały komunikat zasięgu; zagrożenie życia → `emergency=true`; błąd/timeout GLM → komunikat „Agent chwilowo niedostępny”
- **Gotowe gdy:** testy dla wszystkich trzech przypadków

## Faza 3 — Frontend (autor)

### T18 — Czat · `todo` · [A]
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
- GLM: model `glm-5.3`, base URL `https://api.z.ai/api/paas/v4/` (zgodny z OpenAI SDK, tool calling wspierany)

### Faza 0 — postęp
- T02: szkic `docs_ai/api-contract.md` — czeka na akceptację backendu
- T04: `frontend/` — Vite 8 + React 19 + TS + Tailwind 4; zakładki Zapytaj / Mapa / Demo (flaga), pas alarmowy 112 + inne numery, czcionka 18px, Atkinson Hyperlegible Next; vitest 5/5, oxlint OK, build OK

- T03: `docker-compose.yml` (db Postgres 16, api :8000, agent :8001, frontend :5173), Dockerfile dla api/agent (Python 3.12) i frontend (Node 22), Makefile; `/health` api i agent → 200; pytest api 2/2, agent 1/1, vitest 5/5, ruff + oxlint OK; `seed` to stub do T06. Zweryfikowane komendami docker compose (make niezainstalowany)

### Odstępstwa
- Lint frontendu: `oxlint` (domyślny w szablonie Vite) zamiast `eslint`
- Zakładka czatu nazwana „Zapytaj” (czytelniej niż „Czat”)

### Do decyzji autora
- Brak `make` w środowisku Windows (Git Bash) — Makefile z T03 wymaga instalacji make (np. `choco install make`) lub WSL
- Akceptacja kontraktu API przez backend

