import asyncio
import os
import asyncpg


DDL = '''
CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor VARCHAR(128),
    user_id VARCHAR(128),
    event_type VARCHAR(128),
    component VARCHAR(128),
    input_hash VARCHAR(128),
    algorithm_version VARCHAR(64),
    result_summary JSONB,
    details JSONB,
    ip_address VARCHAR(64)
);
'''


async def main():
    url = os.environ.get('TEST_DATABASE_URL') or os.environ.get('DATABASE_URL')
    if not url:
        print('TEST_DATABASE_URL or DATABASE_URL not set')
        return
    conn = await asyncpg.connect(url)
    try:
        await conn.execute(DDL)
        # Attempt hypertable creation (no-op if extension missing)
        try:
            await conn.execute("SELECT create_hypertable('audit_events', 'created_at', if_not_exists => TRUE);")
        except Exception:
            pass
        print('audit_events ensured')
    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(main())
