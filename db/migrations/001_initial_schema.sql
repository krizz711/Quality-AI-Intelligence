CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE measurements (
    id UUID DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL,
    part_number VARCHAR(64) NOT NULL,
    characteristic_name VARCHAR(128) NOT NULL,
    nominal_value DOUBLE PRECISION,
    measured_value DOUBLE PRECISION NOT NULL,
    unit VARCHAR(16),
    operator_id VARCHAR(64),
    equipment_id VARCHAR(64),
    shift VARCHAR(16),
    source_event_id VARCHAR(64) UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(64) DEFAULT 'system',
    PRIMARY KEY (id, timestamp)
);

SELECT create_hypertable('measurements', 'timestamp');

CREATE TABLE grr_studies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    equipment_id VARCHAR(64) NOT NULL,
    characteristic_name VARCHAR(128) NOT NULL,
    status VARCHAR(32) DEFAULT 'pending',
    ev DOUBLE PRECISION,
    av DOUBLE PRECISION,
    pv DOUBLE PRECISION,
    grr_pct DOUBLE PRECISION,
    ndc INTEGER,
    operator_count INTEGER,
    part_count INTEGER,
    acceptance_decision VARCHAR(32),
    report_path TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    reviewed_by VARCHAR(64),
    review_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(64) DEFAULT 'system'
);

CREATE TABLE quality_violations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL,
    part_number VARCHAR(64),
    characteristic_name VARCHAR(128),
    violation_type VARCHAR(64),
    severity VARCHAR(16),
    measured_value DOUBLE PRECISION,
    ucl DOUBLE PRECISION,
    lcl DOUBLE PRECISION,
    alert_sent BOOLEAN DEFAULT FALSE,
    acknowledged_by VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON measurements (part_number, timestamp DESC);
CREATE INDEX ON measurements (equipment_id);
CREATE INDEX ON quality_violations (part_number, timestamp DESC);

CREATE TABLE review_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    study_id UUID NOT NULL REFERENCES grr_studies(id),
    status VARCHAR(32) DEFAULT 'pending',   -- pending/approved/rejected
    assigned_to VARCHAR(64),
    due_at TIMESTAMPTZ,
    decision_notes TEXT,
    decided_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON review_queue (status);
CREATE INDEX ON review_queue (study_id);

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor VARCHAR(128) NOT NULL,
    action VARCHAR(128) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(128) NOT NULL,
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON audit_logs (entity_type, entity_id, created_at DESC);
CREATE INDEX ON audit_logs (actor, created_at DESC);

CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(32) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    message TEXT NOT NULL,
    process_name VARCHAR(128) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    resolved_by VARCHAR(128)
);

CREATE INDEX ON alerts (status, severity, created_at DESC);
CREATE INDEX ON alerts (process_name, created_at DESC);

CREATE TABLE alert_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL REFERENCES alerts(id),
    is_relevant BOOLEAN NOT NULL,
    category VARCHAR(64),
    notes TEXT,
    submitted_by VARCHAR(128) DEFAULT 'quality-engineer',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON alert_feedback (alert_id, created_at DESC);
CREATE INDEX ON alert_feedback (is_relevant, created_at DESC);

CREATE TABLE notification_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID REFERENCES alerts(id),
    channel VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    recipient VARCHAR(256),
    response_reference VARCHAR(128),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON notification_deliveries (alert_id, created_at DESC);
CREATE INDEX ON notification_deliveries (channel, status, created_at DESC);
