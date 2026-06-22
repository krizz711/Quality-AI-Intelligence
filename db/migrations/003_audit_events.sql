-- Migration 003: create audit_events table and Timescale retention policy

BEGIN;

CREATE TABLE IF NOT EXISTS audit_events (
    id UUID DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor VARCHAR(128),
    user_id VARCHAR(128),
    event_type VARCHAR(128) NOT NULL,
    component VARCHAR(128),
    input_hash VARCHAR(128),
    algorithm_version VARCHAR(64),
    result_summary JSONB,
    metadata JSONB,
    ip_address VARCHAR(64),
    PRIMARY KEY (id, created_at)
);

-- If TimescaleDB is available, create a hypertable for time-series management
-- The following will no-op if the extension or function is not present.
DO $$
BEGIN
    IF EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        PERFORM create_hypertable('audit_events', 'created_at', if_not_exists => TRUE);
        -- Create a retention policy of ~5 years (1825 days)
        BEGIN
            PERFORM add_retention_policy('audit_events', INTERVAL '1825 days');
        EXCEPTION WHEN undefined_function THEN
            -- add_retention_policy may not be available depending on Timescale version; ignore
            RAISE NOTICE 'add_retention_policy not available; please add retention manually';
        END;
    END IF;
END$$;

COMMIT;
