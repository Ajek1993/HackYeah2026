from datetime import UTC, datetime, timedelta

NOW = datetime.now(UTC)
FRESH = NOW - timedelta(minutes=20)
STALE = NOW - timedelta(hours=5)

SHELTER_ROW = {
    "shelter_id": "OZO-TEST1",
    "name": "Miejsce ochronne",
    "object_type": "Obiekt ochrony ludności",
    "address": "ul. Testowa 2, Kraków",
    "availability": "Całodobowa",
    "lat": 50.034,
    "lon": 19.92,
}

WARNING_ROW = {
    "warning_key": "hydro:2026:abc:1",
    "source": "hydro",
    "title": "Susza hydrologiczna",
    "severity": -1,
    "body": "Niskie przepływy.",
    "area_descriptions": ["małopolskie, zlewnie Rudawy, Prądnika i przyrzecze Wisły"],
    "valid_from": FRESH,
    "valid_to": None,
    "geometry": None,
}

WATER_ROWS = [
    {
        "station_id": "1",
        "name": "Kraków-Łagiewniki",
        "river": "Wilga",
        "lat": 50.01,
        "lon": 19.93,
        "water_level_cm": 91,
        "warning_level_cm": None,
        "alarm_level_cm": None,
        "level_status": "brak_progow",
        "measured_at": FRESH,
    },
    {
        "station_id": "2",
        "name": "Kraków - Bielany",
        "river": "Wisła",
        "lat": 50.04,
        "lon": 19.84,
        "water_level_cm": 148,
        "warning_level_cm": 370,
        "alarm_level_cm": 520,
        "level_status": "normalny",
        "measured_at": FRESH,
    },
]

OUTAGE_ROW = {
    "id": "uuid@2026-10-05T06:00Z",
    "outage_kind": "planowane",
    "message": "Kraków ul. Testowa 1-10",
    "start_at": FRESH,
    "end_at": NOW + timedelta(hours=2),
    "lat": 50.06,
    "lon": 19.94,
}

AIR_ROW = {
    "provider": "gios",
    "station_id": "400",
    "station_name": "Kraków, Aleja Krasińskiego",
    "index_level": "good",
    "index_label": "Dobry",
    "pm25": 7.8,
    "pm10": 16.5,
    "measured_at": FRESH,
    "last_seen_at": FRESH,
}


class FakeRepo:
    """Stands in for app.repo.Repo; attributes can be overridden per test."""

    def __init__(self, **overrides):
        self.fetched = {
            "shelters": FRESH,
            "power_outages": FRESH,
            "hydro_stations": FRESH,
            "imgw_warnings": FRESH,
            "air_quality_readings": FRESH,
        }
        self.shelters = [SHELTER_ROW]
        self.nearest = [{**SHELTER_ROW, "distance_m": 412}]
        self.warnings = [WARNING_ROW]
        self.water = WATER_ROWS
        self.outages = [OUTAGE_ROW]
        self.air = AIR_ROW
        self.inside: bool | None = True
        self.calls: list[tuple] = []
        for key, value in overrides.items():
            setattr(self, key, value)

    async def last_fetch(self, table):
        return self.fetched[table]

    async def point_in_krakow(self, lat, lon):
        self.calls.append(("point_in_krakow", lat, lon))
        return self.inside

    async def shelters_in_krakow(self):
        return self.shelters

    async def nearest_shelters(self, lat, lon, limit):
        self.calls.append(("nearest_shelters", lat, lon, limit))
        return self.nearest[:limit]

    async def krakow_warnings(self):
        return self.warnings

    async def krakow_water_levels(self):
        return self.water

    async def krakow_power_outages(self):
        return self.outages

    async def freshest_air_quality(self, lat, lon):
        self.calls.append(("freshest_air_quality", lat, lon))
        return self.air
