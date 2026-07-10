-- ============================================================================
-- Migration 003: SQLite-compatible DDL for all tables
-- ============================================================================
-- This file ports 001_core_tables.sql and 002_remaining_tables.sql to SQLite.
--
-- SQLite-specific changes:
--   TEXT instead of UUID (gen_random_uuid() registered in Python)
--   TEXT instead of TIMESTAMPTZ   (now() registered in Python)
--   TEXT instead of JSONB
--   REAL instead of DECIMAL(p,s)
--   INTEGER instead of SMALLINT, BIGSERIAL, BOOLEAN
--   TEXT instead of INTERVAL
--   Generated columns kept (SQLite 3.31+ supports GENERATED ALWAYS AS ... STORED)
--   COMMENT ON statements stripped
--   CREATE EXTENSION stripped
-- ============================================================================

-- ============================================================================
-- 1. users
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id              TEXT            PRIMARY KEY DEFAULT (gen_random_uuid()),
    email           TEXT            NULL        UNIQUE,
    display_name    TEXT            NULL,
    locale          TEXT            NOT NULL    DEFAULT 'en',
    auth_provider   TEXT            NOT NULL    DEFAULT 'anonymous',
    google_sub      TEXT            NULL        UNIQUE,
    created_at      TEXT            NOT NULL    DEFAULT (now()),
    last_active_at  TEXT            NOT NULL    DEFAULT (now()),

    CHECK (auth_provider IN ('anonymous', 'google', 'dev'))
);

-- ============================================================================
-- 2. birth_profiles
-- ============================================================================
CREATE TABLE IF NOT EXISTS birth_profiles (
    id              TEXT            PRIMARY KEY DEFAULT (gen_random_uuid()),
    user_id         TEXT            NOT NULL    UNIQUE,
    birth_date      TEXT            NOT NULL,
    birth_time      TEXT            NULL,
    time_zone       TEXT            NOT NULL,
    utc_offset      TEXT            NULL,
    latitude        REAL            NOT NULL,
    longitude       REAL            NOT NULL,
    location_name   TEXT            NULL,
    house_system    TEXT            NOT NULL    DEFAULT 'P',
    has_unknown_time INTEGER        GENERATED ALWAYS AS (birth_time IS NULL) STORED,
    sun_sign        TEXT            NULL,
    moon_sign       TEXT            NULL,
    rising_sign     TEXT            NULL,
    updated_at      TEXT            NOT NULL    DEFAULT (now()),

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,

    CHECK (latitude >= -90 AND latitude <= 90),
    CHECK (longitude >= -180 AND longitude <= 180),
    CHECK (house_system IN ('P', 'W', 'K', 'E', 'R', 'C', 'V'))
);

-- ============================================================================
-- 3. charts
-- ============================================================================
CREATE TABLE IF NOT EXISTS charts (
    id                  TEXT            PRIMARY KEY DEFAULT (gen_random_uuid()),
    user_id             TEXT            NOT NULL,
    chart_type          TEXT            NOT NULL,
    reference_chart_id  TEXT            NULL,
    title               TEXT            NULL,
    calculation_date    TEXT            NOT NULL,
    house_system        TEXT            NOT NULL,
    location_name       TEXT            NULL,
    latitude            REAL            NOT NULL,
    longitude           REAL            NOT NULL,
    time_zone           TEXT            NOT NULL,
    raw_ephemeris       TEXT            NOT NULL,
    metadata            TEXT            NOT NULL DEFAULT '{}',
    created_at          TEXT            NOT NULL DEFAULT (now()),
    expires_at          TEXT            NULL,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (reference_chart_id) REFERENCES charts(id) ON DELETE SET NULL,

    CHECK (chart_type IN ('natal', 'transit', 'progressed', 'solar_return', 'synastry_composite', 'event')),
    CHECK (house_system IN ('P', 'W', 'K', 'E', 'R', 'C', 'V')),
    CHECK (latitude >= -90 AND latitude <= 90),
    CHECK (longitude >= -180 AND longitude <= 180)
);

-- ============================================================================
-- 4. chart_bodies
-- ============================================================================
CREATE TABLE IF NOT EXISTS chart_bodies (
    id              INTEGER         PRIMARY KEY AUTOINCREMENT,
    chart_id        TEXT            NOT NULL,
    body_key        TEXT            NOT NULL,
    longitude       REAL            NOT NULL,
    latitude        REAL            NOT NULL DEFAULT 0,
    speed           REAL            NOT NULL,
    sign            TEXT            NOT NULL,
    sign_degree     REAL            NOT NULL,
    house           INTEGER         NULL,
    is_retrograde   INTEGER         GENERATED ALWAYS AS (speed < 0) STORED,
    dignity         TEXT            NULL,

    FOREIGN KEY (chart_id) REFERENCES charts(id) ON DELETE CASCADE,

    CHECK (body_key IN (
        'sun', 'moon', 'mercury', 'venus', 'mars',
        'jupiter', 'saturn', 'uranus', 'neptune', 'pluto',
        'north_node', 'south_node', 'chiron',
        'asc', 'mc', 'dsc', 'ic',
        'lilith', 'part_of_fortune'
    )),
    CHECK (longitude >= 0 AND longitude < 360),
    CHECK (sign_degree >= 0 AND sign_degree < 30),
    CHECK (house IS NULL OR (house >= 1 AND house <= 12)),
    CHECK (dignity IS NULL OR dignity IN ('domicile', 'exaltation', 'detriment', 'fall', 'peregrine'))
);

-- ============================================================================
-- 5. chart_houses
-- ============================================================================
CREATE TABLE IF NOT EXISTS chart_houses (
    id              INTEGER         PRIMARY KEY AUTOINCREMENT,
    chart_id        TEXT            NOT NULL,
    house_number    INTEGER         NOT NULL,
    cusps_longitude REAL            NOT NULL,
    sign            TEXT            NOT NULL,
    sign_degree     REAL            NOT NULL,

    FOREIGN KEY (chart_id) REFERENCES charts(id) ON DELETE CASCADE,

    CHECK (house_number >= 1 AND house_number <= 12),
    CHECK (cusps_longitude >= 0 AND cusps_longitude < 360),
    CHECK (sign_degree >= 0 AND sign_degree < 30)
);

-- ============================================================================
-- 6. chart_aspects
-- ============================================================================
CREATE TABLE IF NOT EXISTS chart_aspects (
    id              INTEGER         PRIMARY KEY AUTOINCREMENT,
    chart_id        TEXT            NOT NULL,
    body_a_key      TEXT            NOT NULL,
    body_b_key      TEXT            NOT NULL,
    aspect_type     TEXT            NOT NULL,
    orb             REAL            NOT NULL,
    is_applying     INTEGER         NULL,
    is_major        INTEGER         NOT NULL,

    FOREIGN KEY (chart_id) REFERENCES charts(id) ON DELETE CASCADE,

    CHECK (aspect_type IN (
        'conjunction', 'sextile', 'square', 'trine', 'opposition',
        'quincunx', 'semi_sextile', 'semi_square', 'sesquiquadrate'
    )),
    CHECK (orb >= 0 AND orb <= 10),
    CHECK (body_a_key != body_b_key)
);

-- ============================================================================
-- 7. synastry_pairs
-- ============================================================================
CREATE TABLE IF NOT EXISTS synastry_pairs (
    id                  TEXT            PRIMARY KEY DEFAULT (gen_random_uuid()),
    user_id             TEXT            NOT NULL,
    chart_a_id          TEXT            NOT NULL,
    chart_b_id          TEXT            NOT NULL,
    relationship_type   TEXT            NULL,
    composite_chart_id  TEXT            NULL,
    davison_chart_id    TEXT            NULL,
    score_summary       TEXT            NULL,
    created_at          TEXT            NOT NULL DEFAULT (now()),

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (chart_a_id) REFERENCES charts(id) ON DELETE CASCADE,
    FOREIGN KEY (chart_b_id) REFERENCES charts(id) ON DELETE CASCADE,
    FOREIGN KEY (composite_chart_id) REFERENCES charts(id) ON DELETE SET NULL,
    FOREIGN KEY (davison_chart_id) REFERENCES charts(id) ON DELETE SET NULL,

    CHECK (relationship_type IS NULL OR relationship_type IN (
        'romantic', 'friendship', 'business', 'family'
    )),
    CHECK (chart_a_id != chart_b_id)
);

-- ============================================================================
-- 8. synastry_aspects
-- ============================================================================
CREATE TABLE IF NOT EXISTS synastry_aspects (
    id              INTEGER         PRIMARY KEY AUTOINCREMENT,
    synastry_id     TEXT            NOT NULL,
    chart_a_id      TEXT            NOT NULL,
    chart_b_id      TEXT            NOT NULL,
    body_a_key      TEXT            NOT NULL,
    body_b_key      TEXT            NOT NULL,
    aspect_type     TEXT            NOT NULL,
    orb             REAL            NOT NULL,
    is_applying     INTEGER         NULL,
    house_overlay   TEXT            NULL,

    FOREIGN KEY (synastry_id) REFERENCES synastry_pairs(id) ON DELETE CASCADE,
    FOREIGN KEY (chart_a_id) REFERENCES charts(id) ON DELETE CASCADE,
    FOREIGN KEY (chart_b_id) REFERENCES charts(id) ON DELETE CASCADE,

    CHECK (aspect_type IN (
        'conjunction', 'sextile', 'square', 'trine', 'opposition',
        'quincunx', 'semi_sextile', 'semi_square', 'sesquiquadrate'
    )),
    CHECK (orb >= 0 AND orb <= 10),
    CHECK (body_a_key != body_b_key)
);

-- ============================================================================
-- 9. transit_snapshots
-- ============================================================================
CREATE TABLE IF NOT EXISTS transit_snapshots (
    id              TEXT            PRIMARY KEY DEFAULT (gen_random_uuid()),
    natal_chart_id  TEXT            NOT NULL,
    date_from       TEXT            NOT NULL,
    date_to         TEXT            NOT NULL,
    transit_events  TEXT            NOT NULL,
    created_at      TEXT            NOT NULL DEFAULT (now()),
    expires_at      TEXT            NOT NULL,

    FOREIGN KEY (natal_chart_id) REFERENCES charts(id) ON DELETE CASCADE,

    CHECK (date_from <= date_to)
);

-- ============================================================================
-- 10. life_phases
-- ============================================================================
CREATE TABLE IF NOT EXISTS life_phases (
    id                  INTEGER         PRIMARY KEY AUTOINCREMENT,
    user_id             TEXT            NOT NULL,
    phase_key           TEXT            NOT NULL,
    title               TEXT            NOT NULL,
    start_date          TEXT            NOT NULL,
    end_date            TEXT            NULL,
    dominant_transits   TEXT            NULL,
    description         TEXT            NULL,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,

    CHECK (phase_key IN (
        'foundation', 'saturn_return_1', 'expansion', 'chiron_return',
        'saturn_return_2', 'uranus_opposition', 'legacy'
    )),
    CHECK (end_date IS NULL OR start_date <= end_date)
);

-- ============================================================================
-- 11. conversations
-- ============================================================================
CREATE TABLE IF NOT EXISTS conversations (
    id                  TEXT            PRIMARY KEY DEFAULT (gen_random_uuid()),
    user_id             TEXT            NOT NULL,
    chart_context_id    TEXT            NULL,
    synastry_context_id TEXT            NULL,
    title               TEXT            NULL,
    status              TEXT            NOT NULL DEFAULT 'active',
    model_version       TEXT            NULL,
    created_at          TEXT            NOT NULL DEFAULT (now()),
    updated_at          TEXT            NOT NULL DEFAULT (now()),

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (chart_context_id) REFERENCES charts(id) ON DELETE SET NULL,
    FOREIGN KEY (synastry_context_id) REFERENCES synastry_pairs(id) ON DELETE SET NULL,

    CHECK (status IN ('active', 'archived'))
);

-- ============================================================================
-- 12. messages
-- ============================================================================
CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER         PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT            NOT NULL,
    role            TEXT            NOT NULL,
    content         TEXT            NOT NULL,
    tool_call_id    TEXT            NULL,
    tool_name       TEXT            NULL,
    payload         TEXT            NULL,
    created_at      TEXT            NOT NULL DEFAULT (now()),

    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,

    CHECK (role IN ('system', 'user', 'assistant', 'tool')),
    CHECK (tool_name IS NULL OR tool_name IN (
        'render_natal_chart', 'render_transit_timeline',
        'render_synastry', 'render_life_phases'
    ))
);

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

CREATE INDEX IF NOT EXISTS idx_synastry_aspects_pair
    ON synastry_aspects(synastry_id);

CREATE INDEX IF NOT EXISTS idx_transit_snapshots_natal
    ON transit_snapshots(natal_chart_id, date_from, date_to);

CREATE INDEX IF NOT EXISTS idx_conversations_user
    ON conversations(user_id, status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_messages_conversation
    ON messages(conversation_id, created_at);

-- ============================================================================
-- Done
-- ============================================================================
