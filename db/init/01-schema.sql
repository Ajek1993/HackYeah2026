-- =====================================================================
--  PoC: agent AI, który odpowiadając nanosi obiekty na mapę
--  Schemat bazy: PostgreSQL 15+ / PostGIS 3.x
--
--  Tabele zasilane przez scraper:
--    1. shelters        <- dane.gov.pl, punkty schronienia (plik CSV)          raz na dobę
--    2. power_outages   <- Tauron Dystrybucja, wyłączenia/awarie               co 5–15 min
--    3. hydro_stations  <- IMGW /api/data/hydro (stan bieżący stacji)          co 10–20 min
--    4. imgw_warnings   <- IMGW /api/data/warningshydro + /warningsmeteo       co 5–10 min
--  + słownik geometrii ref_areas, ładowany raz (NIE scrapowany) —
--    bez niego ostrzeżeń IMGW nie da się narysować (API nie zwraca geometrii).
--
--  Wzorzec ładowania (każda tabela):
--    run_ts := now();
--    INSERT ... ON CONFLICT (klucz) DO UPDATE ... last_seen_at = run_ts, is_active = true;
--    UPDATE <tabela> SET is_active = false
--     WHERE <to samo źródło> AND last_seen_at < run_ts AND is_active;
--  Tabela trzyma „stan bieżący”, a to, co zniknęło z feedu, gaśnie.
--
--  Role: scraper pisze (rola scraper_rw), api tylko czyta widoki (rola agent_ro) — patrz koniec pliku.
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS postgis;


-- ---------------------------------------------------------------------
-- 0. Słownik obszarów (statyczny)
--    powiat      : code = TERYT 4 cyfry ('1206')      -> warningsmeteo.teryt[]
--    zlewnia     : code = kod IMGW ('Z_K_MP_2138_A')  -> warningshydro.obszary[].kod_zlewni[]
--    wojewodztwo : code = TERYT 2 cyfry ('12'), name = 'małopolskie'
--                  (fallback, gdy brak geometrii zlewni/powiatu)
--    Źródła: PRG (GUGiK) dla województw/powiatów; geometrię zlewni
--    ostrzeżeń trzeba pozyskać od IMGW — nie jest publikowana w API.
-- ---------------------------------------------------------------------
CREATE TABLE ref_areas (
    area_type  text NOT NULL CHECK (area_type IN ('wojewodztwo', 'powiat', 'zlewnia')),
    code       text NOT NULL,
    name       text,
    geom       geometry(MultiPolygon, 4326) NOT NULL,
    PRIMARY KEY (area_type, code)
);
CREATE INDEX ref_areas_geom_gix ON ref_areas USING gist (geom);
CREATE INDEX ref_areas_name_idx ON ref_areas (area_type, lower(name));


-- ---------------------------------------------------------------------
-- 1. shelters — punkty schronienia (KG PSP przez dane.gov.pl)
--    Pobieranie: plik CSV (UTF-8 z BOM), NIE endpoint /data (nieaktualny, paginacja ucięta):
--      https://api.dane.gov.pl/resources/1393918,punkty-schronienia-dane-csv/file
-- ---------------------------------------------------------------------
CREATE TABLE shelters (
    shelter_id        text PRIMARY KEY,          -- "Identyfikator publiczny", np. OZO-6D94271C9708
    name              text NOT NULL,             -- "Nazwa" (często ogólne: "Miejsce ochronne")
    object_type       text,                      -- "Rodzaj obiektu"
    description       text,                      -- "Opis ogolny" (zwykle pusty)
    address           text,                      -- "Adres"
    gmina             text,
    powiat            text,                      -- 'pow. nyski' albo nazwa miasta na prawach powiatu
    wojewodztwo       text,
    availability      text,                      -- "Dostepnosc": 'Na żądanie', 'Określone godziny', ...
    geom              geometry(Point, 4326) NOT NULL,
    coords_ok         boolean GENERATED ALWAYS AS (
                          ST_X(geom) BETWEEN 14.0 AND 24.2
                      AND ST_Y(geom) BETWEEN 49.0 AND 55.0) STORED,  -- odsiewa zamienione lat/lon
    source_data_date  date,                      -- data_date zasobu z metadanych dane.gov.pl
    row_hash          text NOT NULL,             -- md5 surowego wiersza: wykrywanie zmian
    first_seen_at     timestamptz NOT NULL DEFAULT now(),
    last_seen_at      timestamptz NOT NULL DEFAULT now(),
    is_active         boolean NOT NULL DEFAULT true
);
CREATE INDEX shelters_geom_gix  ON shelters USING gist (geom);
CREATE INDEX shelters_geog_gix  ON shelters USING gist ((geom::geography));  -- ST_DWithin w metrach
CREATE INDEX shelters_admin_idx ON shelters (wojewodztwo, powiat, gmina);


-- ---------------------------------------------------------------------
-- 2. power_outages — wyłączenia i awarie prądu (Tauron)
--    GET /waapi/outages/items?fromDate=<ISO UTC>&toDate=<ISO UTC>
--    Filtr działa „na zakładkę”: zwraca też wyłączenia rozpoczęte wcześniej.
--    UWAGA: OutageId NIE jest unikalny — to samo wyłączenie wraca z kilkoma
--    oknami czasowymi (np. 06:00–08:00 i 14:00–16:00), stąd klucz złożony.
-- ---------------------------------------------------------------------
CREATE TABLE power_outages (
    provider            text        NOT NULL DEFAULT 'tauron',  -- miejsce na innych OSD (PGE, Enea, Energa, Stoen)
    outage_id           uuid        NOT NULL,                   -- OutageId
    start_at            timestamptz NOT NULL,                   -- StartDate (UTC, z 'Z')
    end_at              timestamptz,                            -- EndDate
    type_id             smallint,                               -- TypeId
    outage_kind         text GENERATED ALWAYS AS (
                            CASE type_id WHEN 1 THEN 'planowane'
                                         WHEN 2 THEN 'awaria'   -- wnioskowane z danych: start ≈ moment publikacji
                                         ELSE 'inne' END) STORED,
    message             text NOT NULL,                          -- Message: ulice/numery, wolny tekst
    source_modified_at  timestamptz,                            -- Modified
    region_ids          int[],                                  -- IdsWWW
    address_point_ids   bigint[],                               -- AddressPointIds (wewnętrzne ID Tauronu)
    coords_type         smallint,                               -- CoordinatesType: 0 / 2 / 3
    location_precision  text GENERATED ALWAYS AS (
                            CASE coords_type WHEN 2 THEN 'dokladna'
                                             WHEN 3 THEN 'rejon'  -- wielokąt całego rejonu, nie obszaru wyłączenia!
                                             ELSE 'brak' END) STORED,
    geom                geometry(Geometry, 4326),               -- z Coordinates: 1 pkt -> Point, zamknięty pierścień -> Polygon, inaczej MultiPoint
    center              geometry(Point, 4326),                  -- Center
    radius_m            double precision,                       -- Radius
    source_is_active    boolean,                                -- IsActive
    row_hash            text NOT NULL,
    first_seen_at       timestamptz NOT NULL DEFAULT now(),
    last_seen_at        timestamptz NOT NULL DEFAULT now(),
    is_active           boolean NOT NULL DEFAULT true,
    PRIMARY KEY (provider, outage_id, start_at),
    CHECK (end_at IS NULL OR end_at >= start_at)
);
CREATE INDEX power_outages_geom_gix   ON power_outages USING gist (geom);
CREATE INDEX power_outages_center_gix ON power_outages USING gist (center);
CREATE INDEX power_outages_time_idx   ON power_outages (start_at, end_at) WHERE is_active;


-- ---------------------------------------------------------------------
-- 3. hydro_stations — stacje wodowskazowe IMGW (stan bieżący, 1 wiersz = 1 stacja)
--    Wszystkie pola przychodzą jako stringi; czasy bez strefy (wyglądają na UTC).
--    Feed zbiorczy potrafi stać godzinami — pilnuj measured_at (v_source_freshness).
-- ---------------------------------------------------------------------
CREATE TABLE hydro_stations (
    station_id        text PRIMARY KEY,           -- id_stacji
    name              text NOT NULL,              -- stacja
    river             text,                       -- rzeka (bywa '-', jezioro, Bałtyk)
    wojewodztwo       text,
    geom              geometry(Point, 4326) NOT NULL,
    water_level_cm    integer,                    -- stan_wody
    warning_level_cm  integer,                    -- stan_ostrzegawczy (bywa NULL)
    alarm_level_cm    integer,                    -- stan_alarmowy (bywa NULL)
    flow_m3s          numeric,                    -- przeplyw
    flow_measured_at  timestamptz,                -- przeplyw_data (często inna niż stan_wody)
    water_temp_c      numeric,                    -- temperatura_wody
    measured_at       timestamptz,                -- stan_wody_data_pomiaru
    level_status      text GENERATED ALWAYS AS (
                          CASE
                            WHEN water_level_cm IS NULL                              THEN 'brak_pomiaru'
                            WHEN alarm_level_cm   IS NOT NULL
                             AND water_level_cm >= alarm_level_cm                    THEN 'alarmowy'
                            WHEN warning_level_cm IS NOT NULL
                             AND water_level_cm >= warning_level_cm                  THEN 'ostrzegawczy'
                            WHEN warning_level_cm IS NULL AND alarm_level_cm IS NULL THEN 'brak_progow'
                            ELSE 'normalny'
                          END) STORED,
    raw               jsonb,
    row_hash          text NOT NULL,
    first_seen_at     timestamptz NOT NULL DEFAULT now(),
    last_seen_at      timestamptz NOT NULL DEFAULT now(),
    is_active         boolean NOT NULL DEFAULT true
);
CREATE INDEX hydro_stations_geom_gix  ON hydro_stations USING gist (geom);
CREATE INDEX hydro_stations_geog_gix  ON hydro_stations USING gist ((geom::geography));
CREATE INDEX hydro_stations_river_idx ON hydro_stations (lower(river));


-- ---------------------------------------------------------------------
-- 4. imgw_warnings — ostrzeżenia hydrologiczne i meteorologiczne IMGW
--    source = 'hydro' : obszar = kod_zlewni[]  (rekordy BEZ id w API)
--    source = 'meteo' : obszar = teryt[]       (4-cyfrowe kody powiatów)
--
--    warning_key:
--      'hydro:2026:<8 zn. md5(biuro)>:238'   (numer powtarza się między biurami/wydziałami)
--      'meteo:<id z API>'
--    Puste ostrzeżenia: API zwraca {"message": "Brak ostrzeżeń ..."} (bywa też HTTP 404),
--    a nie pustą tablicę — traktować jako „0 ostrzeżeń”, nie jako błąd.
-- ---------------------------------------------------------------------
CREATE TABLE imgw_warnings (
    warning_key       text PRIMARY KEY,
    source            text NOT NULL CHECK (source IN ('hydro', 'meteo')),
    title             text NOT NULL,              -- zdarzenie / nazwa_zdarzenia: 'Susza hydrologiczna', 'Burze z gradem'
    severity          smallint,                   -- stopień 1..3; -1 = susza hydrologiczna (tak zwraca API)
    probability_pct   smallint,
    valid_from        timestamptz,
    valid_to          timestamptz,                -- NULL = bezterminowo (API: '9999-12-31 23:59:59')
    published_at      timestamptz,
    issuer            text,                       -- biuro
    warning_number    text,                       -- numer (hydro)
    body              text,                       -- przebieg / tresc
    comment           text,                       -- komentarz ("Zmiana dotyczy ...")
    area_codes        text[] NOT NULL DEFAULT '{}',  -- kod_zlewni[] (spłaszczone) albo teryt[]
    voivodeships      text[],                     -- obszary[].wojewodztwo (tylko hydro)
    area_descriptions text[],                     -- obszary[].opis (tylko hydro) — agent może to zacytować
    geom              geometry(Geometry, 4326),   -- wyliczana triggerem z ref_areas
    geom_source       text CHECK (geom_source IN ('obszar_dokladny', 'wojewodztwo_fallback', 'brak')),
    raw               jsonb,
    row_hash          text NOT NULL,
    first_seen_at     timestamptz NOT NULL DEFAULT now(),
    last_seen_at      timestamptz NOT NULL DEFAULT now(),
    is_active         boolean NOT NULL DEFAULT true,
    CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from)
);
CREATE INDEX imgw_warnings_geom_gix  ON imgw_warnings USING gist (geom);
CREATE INDEX imgw_warnings_valid_idx ON imgw_warnings (valid_from, valid_to) WHERE is_active;


-- Geometria ostrzeżeń: najpierw dokładne obszary (zlewnie / powiaty),
-- a jeśli słownik ich nie ma — województwa (zgrubnie, ale coś widać na mapie).
CREATE OR REPLACE FUNCTION imgw_warnings_fill_geom() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    g geometry;
BEGIN
    SELECT ST_Multi(ST_Union(a.geom)) INTO g
      FROM ref_areas a
     WHERE a.area_type = CASE NEW.source WHEN 'meteo' THEN 'powiat' ELSE 'zlewnia' END
       AND a.code = ANY (NEW.area_codes);
    IF g IS NOT NULL THEN
        NEW.geom := g;
        NEW.geom_source := 'obszar_dokladny';
        RETURN NEW;
    END IF;

    SELECT ST_Multi(ST_Union(a.geom)) INTO g
      FROM ref_areas a
     WHERE a.area_type = 'wojewodztwo'
       AND (   lower(a.name) = ANY (SELECT lower(v) FROM unnest(NEW.voivodeships) v)
            OR (NEW.source = 'meteo'
                AND a.code = ANY (SELECT left(c, 2) FROM unnest(NEW.area_codes) c)));
    IF g IS NOT NULL THEN
        NEW.geom := g;
        NEW.geom_source := 'wojewodztwo_fallback';
    ELSE
        NEW.geom := NULL;
        NEW.geom_source := 'brak';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER imgw_warnings_fill_geom
    BEFORE INSERT OR UPDATE OF source, area_codes, voivodeships
    ON imgw_warnings
    FOR EACH ROW EXECUTE FUNCTION imgw_warnings_fill_geom();

-- Po (do)ładowaniu ref_areas przelicz geometrię istniejących ostrzeżeń:
-- UPDATE imgw_warnings SET area_codes = area_codes;


-- =====================================================================
-- Widoki dla agenta (api czyta wyłącznie widoki)
-- =====================================================================

-- Jedna warstwa „wszystko, co da się narysować”, w tym samym kształcie.
-- severity 0..3 służy do koloru na mapie; props trafia do popupu.
CREATE OR REPLACE VIEW v_map_features AS
SELECT 'schron'::text                                   AS layer,
       s.shelter_id                                     AS feature_id,
       s.name                                           AS title,
       s.address                                        AS subtitle,
       0                                                AS severity,
       NULL::timestamptz                                AS valid_from,
       NULL::timestamptz                                AS valid_to,
       'dokladna'::text                                 AS location_precision,
       s.geom,
       jsonb_build_object('rodzaj', s.object_type, 'dostepnosc', s.availability,
                          'gmina', s.gmina, 'powiat', s.powiat)              AS props
  FROM shelters s
 WHERE s.is_active AND s.coords_ok

UNION ALL
SELECT 'prad',
       o.outage_id::text || '@' || to_char(o.start_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI"Z"'),
       CASE o.outage_kind WHEN 'awaria' THEN 'Awaria prądu' ELSE 'Planowane wyłączenie prądu' END,
       left(o.message, 160),
       CASE o.outage_kind WHEN 'awaria' THEN 2 ELSE 1 END,
       o.start_at,
       o.end_at,
       o.location_precision,
       -- rejon (coords_type 3) to wielokąt całego rejonu energetycznego — pokazujemy tylko punkt
       CASE WHEN o.location_precision = 'dokladna' THEN COALESCE(o.geom, o.center) ELSE o.center END,
       jsonb_build_object('komunikat', o.message, 'promien_m', round(o.radius_m),
                          'dostawca', o.provider, 'rodzaj', o.outage_kind)
  FROM power_outages o
 WHERE o.is_active
   AND (o.end_at IS NULL OR o.end_at > now())
   AND o.location_precision <> 'brak'

UNION ALL
SELECT 'stacja_hydro',
       h.station_id,
       COALESCE(h.river || ' – ', '') || h.name,
       h.water_level_cm || ' cm (' || h.level_status || ')',
       CASE h.level_status WHEN 'alarmowy' THEN 3 WHEN 'ostrzegawczy' THEN 2 ELSE 0 END,
       h.measured_at,
       NULL::timestamptz,
       'dokladna',
       h.geom,
       jsonb_build_object('rzeka', h.river, 'stan_cm', h.water_level_cm,
                          'ostrzegawczy_cm', h.warning_level_cm, 'alarmowy_cm', h.alarm_level_cm,
                          'przeplyw_m3s', h.flow_m3s, 'pomiar', h.measured_at,
                          'nieaktualny', h.measured_at < now() - interval '3 hours')
  FROM hydro_stations h
 WHERE h.is_active

UNION ALL
SELECT 'ostrzezenie_' || w.source,
       w.warning_key,
       w.title,
       w.issuer,
       CASE WHEN w.severity = -1 THEN 1                     -- susza
            ELSE GREATEST(COALESCE(w.severity, 0), 0) END,
       w.valid_from,
       w.valid_to,
       CASE w.geom_source WHEN 'wojewodztwo_fallback' THEN 'wojewodztwo' ELSE 'dokladna' END,
       w.geom,
       jsonb_build_object('stopien', w.severity, 'prawdopodobienstwo', w.probability_pct,
                          'tresc', w.body, 'komentarz', w.comment, 'obszary', w.area_descriptions,
                          'opublikowano', w.published_at)
  FROM imgw_warnings w
 WHERE w.is_active
   AND w.geom IS NOT NULL
   AND (w.valid_to IS NULL OR w.valid_to > now());


-- Świeżość źródeł — agent mówi „dane z 13:10”, monitoring alarmuje przy opóźnieniu.
-- Dla stacji hydro: jeśli newest_data jest sprzed > 2 h, to feed zbiorczy stoi.
CREATE OR REPLACE VIEW v_source_freshness AS
SELECT 'shelters'::text   AS source,
       max(last_seen_at)  AS last_fetch,
       max(source_data_date)::timestamptz AS newest_data,
       count(*) FILTER (WHERE is_active)  AS rows_in_last_feed
  FROM shelters
UNION ALL
SELECT 'power_outages', max(last_seen_at),
       max(source_modified_at) FILTER (WHERE is_active), count(*) FILTER (WHERE is_active)
  FROM power_outages
UNION ALL
SELECT 'hydro_stations', max(last_seen_at),
       max(measured_at) FILTER (WHERE is_active), count(*) FILTER (WHERE is_active)
  FROM hydro_stations
UNION ALL
SELECT 'imgw_warnings:' || source, max(last_seen_at),
       max(published_at) FILTER (WHERE is_active), count(*) FILTER (WHERE is_active)
  FROM imgw_warnings
 GROUP BY source;


-- =====================================================================
-- Role: scraper pisze, api tylko czyta widoki
-- (hasła ustawiasz w kontenerze postgres, np. w skrypcie init)
-- =====================================================================
-- CREATE ROLE scraper_rw LOGIN PASSWORD '...';
-- GRANT SELECT, INSERT, UPDATE, DELETE ON shelters, power_outages, hydro_stations, imgw_warnings TO scraper_rw;
-- GRANT SELECT ON ref_areas TO scraper_rw;   -- trigger czyta słownik
--
-- CREATE ROLE agent_ro LOGIN PASSWORD '...';
-- GRANT SELECT ON v_map_features, v_source_freshness TO agent_ro;
-- GRANT SELECT ON shelters, power_outages, hydro_stations, imgw_warnings TO agent_ro;  -- dla narzędzi szczegółowych
-- ALTER ROLE agent_ro SET statement_timeout = '3s';
-- ALTER ROLE agent_ro SET default_transaction_read_only = on;


-- =====================================================================
-- Przykładowe zapytania narzędzi agenta (:lat, :lon, :radius_m)
-- =====================================================================

-- a) find_nearby: 5 najbliższych schronów w promieniu 3 km
-- SELECT shelter_id, name, address, availability,
--        round(ST_Distance(geom::geography, p::geography)) AS dist_m
--   FROM shelters, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) AS p
--  WHERE is_active AND coords_ok
--    AND ST_DWithin(geom::geography, p::geography, 3000)
--  ORDER BY geom <-> p
--  LIMIT 5;

-- b) „Co się dzieje wokół mnie?” — gotowy GeoJSON FeatureCollection dla frontu
-- SELECT json_build_object(
--          'type', 'FeatureCollection',
--          'features', COALESCE(json_agg(ST_AsGeoJSON(t.*)::json), '[]'::json))
--   FROM (SELECT layer, feature_id, title, subtitle, severity, valid_from, valid_to,
--                location_precision, props, geom
--           FROM v_map_features, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) AS p
--          WHERE ST_DWithin(geom::geography, p::geography, :radius_m)) AS t;

-- c) warnings_at_point: ostrzeżenia, których obszar ZAWIERA punkt (a nie „jest blisko”)
-- SELECT warning_key, source, title, severity, valid_from, valid_to, geom_source
--   FROM imgw_warnings
--  WHERE is_active
--    AND (valid_to IS NULL OR valid_to > now())
--    AND ST_Intersects(geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326));

-- d) Scraper: upsert stacji hydro, potem wygaszenie tego, czego nie było w feedzie
-- INSERT INTO hydro_stations (station_id, name, river, wojewodztwo, geom,
--        water_level_cm, warning_level_cm, alarm_level_cm, flow_m3s, measured_at,
--        raw, row_hash, last_seen_at)
-- VALUES ('149200090', 'Dobczyce', 'Raba', 'małopolskie',
--        ST_SetSRID(ST_MakePoint(20.0861, 49.8836), 4326),
--        227, 600, 690, 4.14, '2026-10-03 10:50:00+00', '{...}'::jsonb, md5('...'), :run_ts)
-- ON CONFLICT (station_id) DO UPDATE SET
--        water_level_cm = EXCLUDED.water_level_cm, warning_level_cm = EXCLUDED.warning_level_cm,
--        alarm_level_cm = EXCLUDED.alarm_level_cm, flow_m3s = EXCLUDED.flow_m3s,
--        measured_at = EXCLUDED.measured_at, geom = EXCLUDED.geom, raw = EXCLUDED.raw,
--        row_hash = EXCLUDED.row_hash, last_seen_at = EXCLUDED.last_seen_at, is_active = true;
-- UPDATE hydro_stations SET is_active = false
--  WHERE last_seen_at < :run_ts AND is_active;
