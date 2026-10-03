-- ---------------------------------------------------------------------
-- 5. air_quality_readings — jakość powietrza (GIOŚ, opcjonalnie Airly)
--    1 wiersz = najnowszy odczyt stacji danego dostawcy (stan bieżący).
--    Konflikt źródeł rozstrzyga api: wygrywa najświeższy measured_at (US-04).
--    Na istniejącym wolumenie pgdata wgraj ręcznie (patrz README).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS air_quality_readings (
    provider      text NOT NULL CHECK (provider IN ('gios', 'airly')),
    station_id    text NOT NULL,
    station_name  text NOT NULL,
    geom          geometry(Point, 4326) NOT NULL,
    index_level   text CHECK (index_level IN
                      ('very_good', 'good', 'moderate', 'sufficient', 'bad', 'very_bad')),
    index_label   text,                       -- nazwa kategorii od dostawcy, np. 'Dobry'
    pm25          numeric,
    pm10          numeric,
    measured_at   timestamptz,
    last_seen_at  timestamptz NOT NULL DEFAULT now(),
    is_active     boolean NOT NULL DEFAULT true,
    PRIMARY KEY (provider, station_id)
);
CREATE INDEX IF NOT EXISTS air_quality_geom_gix ON air_quality_readings USING gist (geom);
