-- ============================================================================
-- Migration 001: Core Tables
-- Tables: users, birth_profiles, charts, chart_bodies, chart_houses, chart_aspects
-- ============================================================================

-- ── UUID extension (required for gen_random_uuid()) ─────────────────────────
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- 1. users
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255)    NULL        UNIQUE,
    display_name    VARCHAR(100)    NULL,
    locale          VARCHAR(10)     NOT NULL    DEFAULT 'en',
    created_at      TIMESTAMPTZ     NOT NULL    DEFAULT now(),
    last_active_at  TIMESTAMPTZ     NOT NULL    DEFAULT now()
);

COMMENT ON TABLE  users              IS 'Multi-user root. Lightweight auth (anonymous session or optional email).';
COMMENT ON COLUMN users.email        IS 'Optional identity for magic-link upgrade from anonymous.';
COMMENT ON COLUMN users.display_name IS 'User-facing name shown in chat and chart headers.';
COMMENT ON COLUMN users.locale       IS 'ISO 639-1 language code for i18n (e.g., "en", "de", "fr").';
COMMENT ON COLUMN users.last_active_at IS 'Updated on each authenticated request for session tracking.';

-- ============================================================================
-- 2. birth_profiles
-- ============================================================================
CREATE TABLE IF NOT EXISTS birth_profiles (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID            NOT NULL    UNIQUE,
    birth_date      DATE            NOT NULL,
    birth_time      TIME            NULL,
    time_zone       VARCHAR(50)     NOT NULL,
    utc_offset      INTERVAL        NULL,
    latitude        DECIMAL(8,6)    NOT NULL,
    longitude       DECIMAL(9,6)    NOT NULL,
    location_name   VARCHAR(255)    NULL,
    house_system    VARCHAR(10)     NOT NULL    DEFAULT 'P',
    has_unknown_time BOOLEAN        GENERATED ALWAYS AS (birth_time IS NULL) STORED,
    sun_sign        VARCHAR(20)     NULL,
    moon_sign       VARCHAR(20)     NULL,
    rising_sign     VARCHAR(20)     NULL,
    updated_at      TIMESTAMPTZ     NOT NULL    DEFAULT now(),

    CONSTRAINT fk_birth_profiles_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,

    CONSTRAINT chk_latitude_range
        CHECK (latitude >= -90 AND latitude <= 90),
    CONSTRAINT chk_longitude_range
        CHECK (longitude >= -180 AND longitude <= 180),
    CONSTRAINT chk_house_system
        CHECK (house_system IN ('P', 'W', 'K', 'E', 'R', 'C', 'V'))
);

COMMENT ON TABLE  birth_profiles         IS 'Canonical birth data per user. All charts derive from this unless overridden.';
COMMENT ON COLUMN birth_profiles.time_zone IS 'IANA timezone identifier (e.g., "America/New_York").';
COMMENT ON COLUMN birth_profiles.utc_offset IS 'Computed UTC offset at the moment of birth.';
COMMENT ON COLUMN birth_profiles.house_system IS 'House system code: P=Placidus, W=Whole Sign, K=Koch, E=Equal, etc.';
COMMENT ON COLUMN birth_profiles.has_unknown_time IS 'TRUE when birth_time is NULL (computed via GENERATED column).';
COMMENT ON COLUMN birth_profiles.sun_sign   IS 'Denormalized for quick listings and index queries.';
COMMENT ON COLUMN birth_profiles.moon_sign  IS 'Denormalized for quick listings and index queries.';
COMMENT ON COLUMN birth_profiles.rising_sign IS 'Denormalized; NULL if unknown time.';

-- ============================================================================
-- 3. charts
-- ============================================================================
CREATE TABLE IF NOT EXISTS charts (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID            NOT NULL,
    chart_type          VARCHAR(20)     NOT NULL,
    reference_chart_id  UUID            NULL,
    title               VARCHAR(100)    NULL,
    calculation_date    TIMESTAMPTZ     NOT NULL,
    house_system        VARCHAR(10)     NOT NULL,
    location_name       VARCHAR(255)    NULL,
    latitude            DECIMAL(8,6)    NOT NULL,
    longitude           DECIMAL(9,6)    NOT NULL,
    time_zone           VARCHAR(50)     NOT NULL,
    raw_ephemeris       JSONB           NOT NULL,
    metadata            JSONB           NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),
    expires_at          TIMESTAMPTZ     NULL,

    CONSTRAINT fk_charts_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_charts_reference
        FOREIGN KEY (reference_chart_id) REFERENCES charts(id) ON DELETE SET NULL,

    CONSTRAINT chk_chart_type
        CHECK (chart_type IN ('natal', 'transit', 'progressed', 'solar_return', 'synastry_composite', 'event')),
    CONSTRAINT chk_chart_house_system
        CHECK (house_system IN ('P', 'W', 'K', 'E', 'R', 'C', 'V')),
    CONSTRAINT chk_chart_latitude
        CHECK (latitude >= -90 AND latitude <= 90),
    CONSTRAINT chk_chart_longitude
        CHECK (longitude >= -180 AND longitude <= 180)
);

COMMENT ON TABLE  charts                   IS 'A computed astrological snapshot — natal, transit, progressed, solar return, etc.';
COMMENT ON COLUMN charts.reference_chart_id IS 'For transit/progressed charts, the base natal chart this derives from.';
COMMENT ON COLUMN charts.title             IS 'User-given label, e.g. "My 2025 Solar Return".';
COMMENT ON COLUMN charts.calculation_date  IS 'The moment the chart is calculated for (UTC or timezone-aware).';
COMMENT ON COLUMN charts.house_system      IS 'House system copied from profile at calculation time.';
COMMENT ON COLUMN charts.raw_ephemeris     IS 'Full Swiss Ephemeris output snapshot serialized as JSONB.';
COMMENT ON COLUMN charts.metadata          IS 'Calculation params, ephemeris version, library version, etc.';
COMMENT ON COLUMN charts.expires_at        IS 'Cache TTL for transit/event charts; NULL for permanent natal charts.';

-- ============================================================================
-- 4. chart_bodies
-- ============================================================================
CREATE TABLE IF NOT EXISTS chart_bodies (
    id              BIGSERIAL       PRIMARY KEY,
    chart_id        UUID            NOT NULL,
    body_key        VARCHAR(20)     NOT NULL,
    longitude       DECIMAL(10,7)   NOT NULL,
    latitude        DECIMAL(10,7)   NOT NULL DEFAULT 0,
    speed           DECIMAL(10,7)   NOT NULL,
    sign            VARCHAR(20)     NOT NULL,
    sign_degree     DECIMAL(5,2)    NOT NULL,
    house           SMALLINT        NULL,
    is_retrograde   BOOLEAN         GENERATED ALWAYS AS (speed < 0) STORED,
    dignity         VARCHAR(20)     NULL,

    CONSTRAINT fk_chart_bodies_chart
        FOREIGN KEY (chart_id) REFERENCES charts(id) ON DELETE CASCADE,

    CONSTRAINT chk_body_key
        CHECK (body_key IN (
            'sun', 'moon', 'mercury', 'venus', 'mars',
            'jupiter', 'saturn', 'uranus', 'neptune', 'pluto',
            'north_node', 'south_node', 'chiron',
            'asc', 'mc', 'dsc', 'ic',
            'lilith', 'part_of_fortune'
        )),
    CONSTRAINT chk_body_longitude
        CHECK (longitude >= 0 AND longitude < 360),
    CONSTRAINT chk_body_sign_degree
        CHECK (sign_degree >= 0 AND sign_degree < 30),
    CONSTRAINT chk_body_house
        CHECK (house IS NULL OR (house >= 1 AND house <= 12)),
    CONSTRAINT chk_body_dignity
        CHECK (dignity IS NULL OR dignity IN ('domicile', 'exaltation', 'detriment', 'fall', 'peregrine'))
);

COMMENT ON TABLE  chart_bodies              IS 'Planetary positions, angles, nodes, and other celestial bodies in a chart.';
COMMENT ON COLUMN chart_bodies.body_key     IS 'Identifier: sun, moon, mercury, venus, mars, jupiter, saturn, uranus, neptune, pluto, north_node, south_node, chiron, asc, mc, dsc, ic, lilith, part_of_fortune.';
COMMENT ON COLUMN chart_bodies.longitude    IS 'Ecliptic longitude 0–360 degrees.';
COMMENT ON COLUMN chart_bodies.speed        IS 'Degrees per day; negative indicates retrograde motion.';
COMMENT ON COLUMN chart_bodies.sign         IS 'Zodiac sign: aries, taurus, gemini, cancer, leo, virgo, libra, scorpio, sagittarius, capricorn, aquarius, pisces.';
COMMENT ON COLUMN chart_bodies.house        IS 'House number 1–12; NULL if unknown time or no house computation.';
COMMENT ON COLUMN chart_bodies.is_retrograde IS 'Computed: TRUE when speed < 0.';
COMMENT ON COLUMN chart_bodies.dignity      IS 'Essential dignity: domicile, exaltation, detriment, fall, peregrine.';

-- ============================================================================
-- 5. chart_houses
-- ============================================================================
CREATE TABLE IF NOT EXISTS chart_houses (
    id              BIGSERIAL       PRIMARY KEY,
    chart_id        UUID            NOT NULL,
    house_number    SMALLINT        NOT NULL,
    cusps_longitude DECIMAL(10,7)   NOT NULL,
    sign            VARCHAR(20)     NOT NULL,
    sign_degree     DECIMAL(5,2)    NOT NULL,

    CONSTRAINT fk_chart_houses_chart
        FOREIGN KEY (chart_id) REFERENCES charts(id) ON DELETE CASCADE,

    CONSTRAINT chk_house_number
        CHECK (house_number >= 1 AND house_number <= 12),
    CONSTRAINT chk_house_cusps_longitude
        CHECK (cusps_longitude >= 0 AND cusps_longitude < 360),
    CONSTRAINT chk_house_sign_degree
        CHECK (sign_degree >= 0 AND sign_degree < 30)
);

COMMENT ON TABLE  chart_houses IS 'House cusps for a given chart — one row per house (12 rows per chart).';

-- ============================================================================
-- 6. chart_aspects
-- ============================================================================
CREATE TABLE IF NOT EXISTS chart_aspects (
    id              BIGSERIAL       PRIMARY KEY,
    chart_id        UUID            NOT NULL,
    body_a_key      VARCHAR(20)     NOT NULL,
    body_b_key      VARCHAR(20)     NOT NULL,
    aspect_type     VARCHAR(20)     NOT NULL,
    orb             DECIMAL(5,2)    NOT NULL,
    is_applying     BOOLEAN         NULL,
    is_major        BOOLEAN         NOT NULL,

    CONSTRAINT fk_chart_aspects_chart
        FOREIGN KEY (chart_id) REFERENCES charts(id) ON DELETE CASCADE,

    CONSTRAINT chk_aspect_type
        CHECK (aspect_type IN (
            'conjunction', 'sextile', 'square', 'trine', 'opposition',
            'quincunx', 'semi_sextile', 'semi_square', 'sesquiquadrate'
        )),
    CONSTRAINT chk_aspect_orb
        CHECK (orb >= 0 AND orb <= 10),
    CONSTRAINT chk_aspect_bodies_distinct
        CHECK (body_a_key != body_b_key)
);

COMMENT ON TABLE  chart_aspects           IS 'Precomputed aspects between bodies in a single chart (intra-chart).';
COMMENT ON COLUMN chart_aspects.body_a_key IS 'First body in the aspect pair.';
COMMENT ON COLUMN chart_aspects.body_b_key IS 'Second body in the aspect pair.';
COMMENT ON COLUMN chart_aspects.orb       IS 'Degrees of separation from exact aspect (0 = exact).';
COMMENT ON COLUMN chart_aspects.is_applying IS 'TRUE if aspect is applying; FALSE if separating; NULL if stationary.';
COMMENT ON COLUMN chart_aspects.is_major  IS 'TRUE for conjunction, sextile, square, trine, opposition.';

-- ============================================================================
-- Indexes
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_charts_user_type
    ON charts(user_id, chart_type);

CREATE INDEX IF NOT EXISTS idx_chart_bodies_chart
    ON chart_bodies(chart_id);

CREATE INDEX IF NOT EXISTS idx_chart_bodies_sign
    ON chart_bodies(sign);

CREATE INDEX IF NOT EXISTS idx_chart_bodies_body_key
    ON chart_bodies(chart_id, body_key);

CREATE INDEX IF NOT EXISTS idx_chart_aspects_chart
    ON chart_aspects(chart_id);

-- ============================================================================
-- Done
-- ============================================================================
