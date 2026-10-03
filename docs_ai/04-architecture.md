# 04 — Architektura

> KryzIO · tryb uproszczony · skala: PoC hackathonowy (bez kont, bez trwałego zapisu danych użytkownika)

## Decyzje

| Obszar | Decyzja | Dlaczego / odrzucone |
|---|---|---|
| Repo | Monorepo w tym repozytorium (publiczne) | jeden link w zgłoszeniu |
| Uruchomienie | Docker + `docker-compose.yml`, osobne kontenery | wymóg autora; jedno polecenie startu |
| Kontener `frontend` | React + Vite + TypeScript + Tailwind, Leaflet + OSM | autor: „nie ma znaczenia” → najszybszy start; duża czcionka / kontrast łatwe w Tailwind |
| Kontener `api` | Python + FastAPI; pobieranie danych (`requests` / scraping), harmonogram odświeżania, REST dla frontu i agenta | wybór backendowca |
| Kontener `agent` | Python + FastAPI; agent AI na **GLM 5.3** (klucz autora) z tool calling; narzędzia wołają `api` | separacja: agent nie scrapuje, tylko korzysta z danych `api` → odpowiedzi tylko z danych, ze źródłem i datą |
| Kontener `db` | PostgreSQL — cache odczytów ze źródeł (z timestampem), dane schronów | osobny kontener wymagany przez autora; SQLite odrzucony |
| Schrony | Realne źródło dostarczone przez backend, zapisane jako JSON w repo, ładowane do `db` | stabilne na demo |
| Poradnik | Fragmenty Poradnika bezpieczeństwa jako lokalne pliki tekstowe, dostępne dla agenta jako narzędzie `get_guide` | wiarygodny, stały materiał |
| Odświeżanie | Zadanie w tle w `api`; Airly co 2h (rate limit), pozostałe źródła częściej | demo nie zależy od dostępności cudzych stron |
| Geokodowanie | Nominatim (OSM), walidacja „czy adres w Krakowie” | darmowe; realizuje US-01 |
| Demo | Flaga `DEMO_MODE` — `api` zwraca symulowane dane scenariusza (powódź / brak prądu / atak bombowy); front pokazuje zakładkę Demo tylko przy włączonej fladze | ten sam kod agenta w obu trybach; Demo nie trafia do docelowej aplikacji |
| Sekrety | `.env` (w `.gitignore`), w repo `.env.example` | repo publiczne |
| Testy | `pytest` (api, agent), `vitest` (frontend) | |
| Makefile | cele m.in. `up`, `down`, `test`, `test-api`, `test-agent`, `test-frontend`, `lint` | wymóg autora |
| README | opis projektu, uruchomienie, architektura, źródła danych, ujawnienie użycia AI i zewnętrznych API (wymóg HackYeah) | |
| Hosting demo | `frontend` na **Vercel**; `api` + `agent` + `db` w docker-compose na **własnym VPS** zespołu | Vercel nie uruchamia kontenerów; VPS już jest. Wymaga HTTPS na VPS (reverse proxy) i CORS dla domeny Vercela |

## Przepływ

```
frontend ──► agent ──(tool calls)──► api ──► db (cache)
    │                                  ▲
    └──────────► api (mapa, panel)     └── harmonogram: IMGW, Tauron, GIOŚ, Airly, poradnik
```

## Świadomie nie robimy

- Kubernetes, mikroserwisy ponad 4 kontenery, kolejki, Redis
- Konta, autoryzacja, zapis rozmów na serwerze
- Własnego modelu predykcji zalania — tylko dane ze źródeł

## Otwarte pytania / założenia — rozstrzygnięte

- A7: frontend na Vercel, backend (api, agent, db) na własnym VPS
- A8: FastAPI + `requests`, bez Flaska
- A9: 4 kontenery — `frontend`, `api`, `agent`, `db` (lokalnie wszystkie w docker-compose; na produkcji `frontend` z Vercela)
