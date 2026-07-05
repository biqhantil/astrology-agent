-- ============================================================================
-- Migration 002: Remaining Tables
-- Tables: synastry_pairs, synastry_aspects, transit_snapshots,
--         life_phases, conversations, messages
-- ============================================================================

-- ============================================================================
-- 7. synastry_pairs
-- ============================================================================
CREATE TABLE IF NOT EXISTS synastry_pairs (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID            NOT NULL,
    chart_a_id          UUID            NOT NULL,
    chart_b_id          UUID            NOT NULL,
    relationship_type   VARCHAR(30)     NULL,
    composite_chart_id  UUID            NULL,
    davison_chart_id    UUID            NULL,
    score_summary       JSONB           NULL,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT fk_synastry_pairs_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_synastry_pairs_chart_a
        FOREIGN KEY (chart_a_id) REFERENCES charts(id) ON DELETE CASCADE,
    CONSTRAINT fk_synastry_pairs_chart_b
        FOREIGN KEY (chart_b_id) REFERENCES charts(id) ON DELETE CASCADE,
    CONSTRAINT fk_synastry_pairs_composite
        FOREIGN KEY (composite_chart_id) REFERENCES charts(id) ON DELETE SET NULL,
    CONSTRAINT fk_synastry_pairs_davison
        FOREIGN KEY (davison_chart_id) REFERENCES charts(id) ON DELETE SET NULL,

    CONSTRAINT chk_relationship_type
        CHECK (relationship_type IS NULL OR relationship_type IN (
            'romantic', 'friendship', 'business', 'family'
        )),
    CONSTRAINT chk_synastry_charts_distinct
        CHECK (chart_a_id != chart_b_id)
);

COMMENT ON TABLE  synastry_pairs           IS 'Links two charts for synastry / compatibility analysis.';
COMMENT ON COLUMN synastry_pairs.user_id   IS 'Owner/initiator of the synastry comparison.';
COMMENT ON COLUMN synastry_pairs.chart_a_id IS 'First chart (typically the initiator/owner natal).';
COMMENT ON COLUMN synastry_pairs.chart_b_id IS 'Second chart (partner/other person natal).';
COMMENT ON COLUMN synastry_pairs.composite_chart_id IS 'Optional composite midpoint chart.';
COMMENT ON COLUMN synastry_pairs.davison_chart_id   IS 'Optional Davison relationship chart.';
COMMENT ON COLUMN synastry_pairs.score_summary      IS 'Aggregated compatibility metrics {emotional, communication, passion, commitment, overall}.';

-- ============================================================================
-- 8. synastry_aspects
-- ============================================================================
CREATE TABLE IF NOT EXISTS synastry_aspects (
    id              BIGSERIAL       PRIMARY KEY,
    synastry_id     UUID            NOT NULL,
    chart_a_id      UUID            NOT NULL,
    chart_b_id      UUID            NOT NULL,
    body_a_key      VARCHAR(20)     NOT NULL,
    body_b_key      VARCHAR(20)     NOT NULL,
    aspect_type     VARCHAR(20)     NOT NULL,
    orb             DECIMAL(5,2)    NOT NULL,
    is_applying     BOOLEAN         NULL,
    house_overlay   JSONB           NULL,

    CONSTRAINT fk_synastry_aspects_pair
        FOREIGN KEY (synastry_id) REFERENCES synastry_pairs(id) ON DELETE CASCADE,
    CONSTRAINT fk_synastry_aspects_chart_a
        FOREIGN KEY (chart_a_id) REFERENCES charts(id) ON DELETE CASCADE,
    CONSTRAINT fk_synastry_aspects_chart_b
        FOREIGN KEY (chart_b_id) REFERENCES charts(id) ON DELETE CASCADE,

    CONSTRAINT chk_synastry_aspect_type
        CHECK (aspect_type IN (
            'conjunction', 'sextile', 'square', 'trine', 'opposition',
            'quincunx', 'semi_sextile', 'semi_square', 'sesquiquadrate'
        )),
    CONSTRAINT chk_synastry_orb
        CHECK (orb >= 0 AND orb <= 10),
    CONSTRAINT chk_synastry_bodies_distinct
        CHECK (body_a_key != body_b_key)
);

COMMENT ON TABLE  synastry_aspects           IS 'Inter-chart aspects (Chart A body vs Chart B body). Kept separate from chart_aspects for clarity.';
COMMENT ON COLUMN synastry_aspects.chart_a_id IS 'Denormalized for partition pruning and query efficiency.';
COMMENT ON COLUMN synastry_aspects.chart_b_id IS 'Denormalized for partition pruning and query efficiency.';
COMMENT ON COLUMN synastry_aspects.house_overlay IS 'Metadata like {body_a: "mars", in_house_b: 7}.';

-- ============================================================================
-- 9. transit_snapshots
-- ============================================================================
CREATE TABLE IF NOT EXISTS transit_snapshots (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    natal_chart_id  UUID            NOT NULL,
    date_from       DATE            NOT NULL,
    date_to         DATE            NOT NULL,
    transit_events  JSONB           NOT NULL,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ     NOT NULL,

    CONSTRAINT fk_transit_snapshots_natal
        FOREIGN KEY (natal_chart_id) REFERENCES charts(id) ON DELETE CASCADE,

    CONSTRAINT chk_transit_date_range
        CHECK (date_from <= date_to)
);

COMMENT ON TABLE  transit_snapshots        IS 'Time-series cache of transits against a natal chart.';
COMMENT ON COLUMN transit_snapshots.transit_events IS 'Array of transit event objects: {date, transiting_body, natal_body, aspect_type, orb, exact_date, ...}.';
COMMENT ON COLUMN transit_snapshots.expires_at     IS 'Eviction timestamp for cache TTL.';

-- ============================================================================
-- 10. life_phases
-- ============================================================================
CREATE TABLE IF NOT EXISTS life_phases (
    id                  BIGSERIAL       PRIMARY KEY,
    user_id             UUID            NOT NULL,
    phase_key           VARCHAR(30)     NOT NULL,
    title               VARCHAR(100)    NOT NULL,
    start_date          DATE            NOT NULL,
    end_date            DATE            NULL,
    dominant_transits   JSONB           NULL,
    description         TEXT            NULL,

    CONSTRAINT fk_life_phases_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,

    CONSTRAINT chk_phase_key
        CHECK (phase_key IN (
            'foundation', 'saturn_return_1', 'expansion', 'chiron_return',
            'saturn_return_2', 'uranus_opposition', 'legacy'
        )),
    CONSTRAINT chk_phase_dates
        CHECK (end_date IS NULL OR start_date <= end_date)
);

COMMENT ON TABLE  life_phases              IS 'Precomputed major life phases derived from Saturn returns, Uranus opposition, nodal returns, etc.';
COMMENT ON COLUMN life_phases.phase_key    IS 'Machine key identifying the phase type.';
COMMENT ON COLUMN life_phases.title        IS 'Human-readable phase label.';
COMMENT ON COLUMN life_phases.start_date   IS 'Approximate start date of the phase.';
COMMENT ON COLUMN life_phases.end_date     IS 'Approximate end date; NULL for the currently active phase.';
COMMENT ON COLUMN life_phases.dominant_transits IS 'Array of key transits defining this phase: [{planet, aspect, natal_body, date}].';
COMMENT ON COLUMN life_phases.description  IS 'LLM-generated or templated phase description.';

-- ============================================================================
-- 11. conversations
-- ============================================================================
CREATE TABLE IF NOT EXISTS conversations (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID            NOT NULL,
    chart_context_id    UUID            NULL,
    synastry_context_id UUID            NULL,
    title               VARCHAR(200)    NULL,
    status              VARCHAR(20)     NOT NULL DEFAULT 'active',
    model_version       VARCHAR(50)     NULL,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT fk_conversations_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_conversations_chart
        FOREIGN KEY (chart_context_id) REFERENCES charts(id) ON DELETE SET NULL,
    CONSTRAINT fk_conversations_synastry
        FOREIGN KEY (synastry_context_id) REFERENCES synastry_pairs(id) ON DELETE SET NULL,

    CONSTRAINT chk_conversation_status
        CHECK (status IN ('active', 'archived'))
);

COMMENT ON TABLE  conversations                IS 'Chat sessions. One active conversation per user at a time; historicals archived.';
COMMENT ON COLUMN conversations.chart_context_id IS 'Chart loaded into the LLM system prompt for this conversation.';
COMMENT ON COLUMN conversations.synastry_context_id IS 'Synastry pair loaded when comparing two charts.';
COMMENT ON COLUMN conversations.title          IS 'Auto-generated from the first user query for display.';
COMMENT ON COLUMN conversations.status         IS 'active | archived. Only one active conversation per user is expected.';
COMMENT ON COLUMN conversations.model_version  IS 'Snapshot of the LLM model version used for this conversation.';

-- ============================================================================
-- 12. messages
-- ============================================================================
CREATE TABLE IF NOT EXISTS messages (
    id              BIGSERIAL       PRIMARY KEY,
    conversation_id UUID            NOT NULL,
    role            VARCHAR(20)     NOT NULL,
    content         TEXT            NOT NULL,
    tool_call_id    VARCHAR(50)     NULL,
    tool_name       VARCHAR(50)     NULL,
    payload         JSONB           NULL,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT fk_messages_conversation
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,

    CONSTRAINT chk_message_role
        CHECK (role IN ('system', 'user', 'assistant', 'tool')),
    CONSTRAINT chk_message_tool_name
        CHECK (tool_name IS NULL OR tool_name IN (
            'render_natal_chart', 'render_transit_timeline',
            'render_synastry', 'render_life_phases'
        ))
);

COMMENT ON TABLE  messages                  IS 'Individual chat turns. Stores both visible text and hidden structured tool payloads.';
COMMENT ON COLUMN messages.role             IS 'system | user | assistant | tool — mirrors OpenAI/Anthropic message roles.';
COMMENT ON COLUMN messages.content          IS 'Visible markdown text or JSON string for tool messages.';
COMMENT ON COLUMN messages.tool_call_id     IS 'Links assistant tool_use to tool result message (for multi-turn tool flows).';
COMMENT ON COLUMN messages.tool_name        IS 'Tool identifier when this message is a tool call/result.';
COMMENT ON COLUMN messages.payload          IS 'Structured data for tool renders (chart data, transit events, etc.).';

-- ============================================================================
-- Indexes
-- ============================================================================
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
