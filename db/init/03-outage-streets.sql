-- =====================================================================
-- Street-level location of power outages (Tauron)
--
-- Most Kraków outages come with CoordinatesType 3: `center` is then the centre of
-- the whole power district (Kraków: Rynek Główny), so every outage lands on the
-- same point. The first address from the message is geocoded (Nominatim) into
-- `street_center`; `geocode_cache` keeps the results between refreshes.
-- Only public outage addresses are stored here, never user input.
-- =====================================================================

ALTER TABLE power_outages ADD COLUMN IF NOT EXISTS street_center geometry(Point, 4326);

CREATE TABLE IF NOT EXISTS geocode_cache (
    query       text PRIMARY KEY,                -- e.g. 'Szuwarowa 4, Kraków'
    found       boolean NOT NULL,
    lat         double precision,
    lon         double precision,
    fetched_at  timestamptz NOT NULL DEFAULT now(),
    CHECK (NOT found OR (lat IS NOT NULL AND lon IS NOT NULL))
);
