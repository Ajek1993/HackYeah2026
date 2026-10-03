# API contract — KryzIO

> Status: **draft** — to be accepted by frontend/agent author and backend author (task T02).
> Changes after acceptance = SPEC "Ask First".

## Services

| Service | Port (local) | Consumers |
|---------|--------------|-----------|
| `api` | 8000 | `agent`, `frontend` (map, summary, demo) |
| `agent` | 8001 | `frontend` (chat) |

- JSON everywhere, UTF-8, timestamps ISO 8601 with timezone (`2026-10-04T10:30:00+02:00`)
- Coordinates: WGS84, `lat` / `lon` as floats
- CORS: origins from `CORS_ORIGINS`
- No endpoint logs user addresses or chat content

## Common envelope for data readings

Every endpoint returning data from an external source wraps it like this:

```json
{
  "source": "IMGW",
  "source_url": "https://danepubliczne.imgw.pl/",
  "updated_at": "2026-10-04T10:30:00+02:00",
  "is_stale": false,
  "is_simulated": false,
  "data": { }
}
```

- `source` — human-readable source name shown to the user
- `updated_at` — when KryzIO last fetched the source (not when the request was made), in Kraków time (`+02:00` / `+01:00`); for the static safety guide: its publication date
- `is_stale` — `true` when `updated_at` is older than 3h (always `false` for the safety guide)
- `is_simulated` — `true` only when a demo scenario is active
- `data` — `null` when there is no cached data at all ("Brak danych")

Endpoints aggregating several sources return a list of envelopes.

## `api` endpoints

### `GET /health`
`200 {"status": "ok", "demo_mode": false}`

### `GET /geocode?q=Kobierzyńska 1, Kraków`
```json
{
  "query": "Kobierzyńska 1, Kraków",
  "found": true,
  "lat": 50.0335,
  "lon": 19.9205,
  "display_name": "Kobierzyńska, Dębniki, Kraków",
  "district": "Dębniki",
  "in_krakow": true
}
```
- Not found → `200` with `found: false`, other fields `null`
- Outside Kraków → `in_krakow: false`

### `GET /reverse?lat=&lon=`
Reverse geocoding of the user's device location (Nominatim reverse). Same shape as `/geocode`, `query` is `null`.
```json
{
  "query": null,
  "found": true,
  "lat": 50.0312,
  "lon": 19.9204,
  "display_name": "Kobierzyńska, Dębniki, Kraków",
  "district": "Dębniki",
  "in_krakow": true
}
```
- Not found → `200` with `found: false`
- Coordinates are personal data: never logged (also not in access logs)

### `GET /warnings?lat=&lon=`
Active meteorological and hydrological warnings relevant to the point (or all of Kraków when no coordinates).
```json
{
  "source": "IMGW", "source_url": "...", "updated_at": "...", "is_stale": false, "is_simulated": false,
  "data": [
    {
      "id": "imgw-hydro-123",
      "kind": "flood",
      "level": 2,
      "title": "Wezbranie z przekroczeniem stanów ostrzegawczych",
      "description": "...",
      "area": "Wisła, Kraków",
      "valid_from": "...",
      "valid_to": "...",
      "geometry": null
    }
  ]
}
```
- `kind`: `flood` | `storm` | `wind` | `heat` | `frost` | `drought` | `fire` | `bomb_threat` | `other`
- Kraków-wide: meteo warnings for TERYT 1261, hydro warnings for catchments covering Kraków; `lat` / `lon` accepted but not used for filtering
- `level`: 1–3 (IMGW scale); `geometry`: GeoJSON or `null`

### `GET /water-levels`
```json
{
  "source": "IMGW", "...": "...",
  "data": [
    {
      "station": "Kraków-Bielany",
      "river": "Wisła",
      "lat": 50.04, "lon": 19.84,
      "level_cm": 312,
      "warning_cm": 450,
      "alarm_cm": 550,
      "trend": "rising",
      "measured_at": "..."
    }
  ]
}
```
- `trend`: `rising` | `falling` | `stable` | `null` (currently always `null`: no measurement history is stored)
- Extra field `status`: `normal` | `warning` | `alarm` | `unknown` (no thresholds published)
- Stations inside Kraków or within 15 km of the centre, closest first

### `GET /air-quality?lat=&lon=`
Freshest reading from GIOŚ or Airly (conflict rule: freshest wins). Envelope `source` says which one was used.
```json
{
  "source": "GIOŚ", "...": "...",
  "data": {
    "station": "Kraków, al. Krasińskiego",
    "index": "bad",
    "index_label": "Zły",
    "pm25": 78.0,
    "pm10": 110.0,
    "measured_at": "..."
  }
}
```
- `index`: `very_good` | `good` | `moderate` | `sufficient` | `bad` | `very_bad`
- Nearest station with an index within 10 km of the point (default: city centre); `pm25` / `pm10` may be `null`
- `data: null` when no station has a current index

### `GET /power-outages?lat=&lon=`
```json
{
  "source": "Tauron Dystrybucja", "...": "...",
  "data": [
    {
      "id": "tauron-456",
      "planned": true,
      "area": "Kraków, ul. Kobierzyńska 1-50",
      "start": "...",
      "end": "...",
      "lat": 50.03, "lon": 19.92
    }
  ]
}
```

### `GET /shelters`
```json
{
  "source": "<shelter data source>", "...": "...",
  "data": [
    { "id": "s-1", "name": "...", "address": "...", "lat": 50.0, "lon": 19.9, "capacity": 120, "type": "shelter" }
  ]
}
```
- `type`: `shelter` | `hiding_place` (`shelter` only when the source names the object a "schron")
- `capacity`: `null` — not published by the source
- Extra field `availability`: e.g. `Całodobowa`, `Na żądanie`, `Określone godziny`
- `GET /shelters` returns shelters inside Kraków

### `GET /shelters/nearest?lat=&lon=&limit=3`
Same envelope, `data` = list sorted by distance, each item extended with `distance_m` (integer).

### `GET /guide/{topic}`
- `topic`: `flood` | `power_outage` | `bomb_threat` | `fire` | `drought` | `air_quality` | `general`
```json
{
  "source": "Poradnik bezpieczeństwa", "...": "...",
  "data": {
    "topic": "flood",
    "title": "Powódź",
    "before": ["..."],
    "during": ["..."],
    "after": ["..."],
    "emergency_numbers": [{"name": "Numer alarmowy", "number": "112"}]
  }
}
```
- Unknown topic → `404`
- Topic not covered by the guide (`drought`, `air_quality`) → `data: null`

### `GET /summary`
Data for the map tab tiles — one request, all sources.
```json
{
  "generated_at": "...",
  "demo_scenario": null,
  "tiles": [
    { "kind": "warnings", "status": "warning", "headline": "1 ostrzeżenie hydrologiczne", "source": "IMGW", "updated_at": "...", "is_stale": false, "is_simulated": false },
    { "kind": "water", "status": "ok", "headline": "Wisła: 312 cm (ostrzegawczy 450)", "...": "..." },
    { "kind": "air", "status": "danger", "headline": "Jakość powietrza: zła", "...": "..." },
    { "kind": "power", "status": "warning", "headline": "3 wyłączenia prądu", "...": "..." }
  ]
}
```
- `status`: `ok` | `warning` | `danger` | `no_data`

### Demo (only when `DEMO_MODE=true`, otherwise `404`)

- `GET /demo/scenarios` → `[{"id": "flood", "title": "Powódź"}, {"id": "power_outage", "title": "Brak prądu"}, {"id": "bomb_threat", "title": "Atak bombowy"}]`
- `POST /demo/activate/{id}` → `{"active": "flood"}`; while active, data endpoints return simulated data with `is_simulated: true`
- `POST /demo/deactivate` → `{"active": null}`

## `agent` endpoints

### `GET /health`
`200 {"status": "ok", "model": "glm-5.3"}`

### `POST /chat`
Request:
```json
{
  "session_id": "uuid-from-frontend",
  "message": "Czy grozi mi zalanie?",
  "location": { "lat": 50.0312, "lon": 19.9204, "accuracy_m": 25 }
}
```
- `location` optional (`null` when the user denied it); sent with every request, never stored in the session
- A place named in `message` takes precedence over `location`
Response:
```json
{
  "session_id": "uuid-from-frontend",
  "answer": "markdown text in Polish",
  "sections": {
    "situation": "...",
    "before": ["..."],
    "during": ["..."],
    "after": ["..."]
  },
  "sources": [
    { "name": "IMGW", "url": "...", "updated_at": "...", "is_stale": false }
  ],
  "emergency": false,
  "out_of_area": false,
  "off_topic": false,
  "is_simulated": false,
  "disclaimer": "KryzIO nie zastępuje komunikatów służb. ..."
}
```
- `sections` may be `null` (clarifying question, off-topic, out of area)
- `emergency: true` → frontend shows the "Dzwoń 112" banner
- LLM error / timeout → `503 {"error": "agent_unavailable", "message": "Agent chwilowo niedostępny"}`
- Session context lives in agent memory only (TTL), never in `db` or logs

### `DELETE /chat/{session_id}`
Clears session context. `204`.
