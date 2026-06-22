import asyncio
import os
import uuid
import asyncpg

# Read DB URL from TEST_DATABASE_URL
DB_URL = os.environ.get("TEST_DATABASE_URL")
if not DB_URL:
    raise RuntimeError("TEST_DATABASE_URL must be set to run this script.")

USERS = [
    (
        "88bfcab2-7dde-4de9-938a-b1f457b68845",
        "admin",
        "$2b$12$RJA.K1CLDZ9BER28jbpmhe8bgNFP0xcwInEu81sNj2ckSAD9Mlw9C",
    ),
    (
        "151d6469-dfd7-45e7-a045-f67c905c42ad",
        "quality_engineer",
        "$2b$12$wEz9U18MOvVJguiiVM69peOIMMjy0NDJulcByMP0WTpjlulj6v2Fm",
    ),
    (
        "00000000-0000-0000-0000-000000000001",
        "testuser",
        "$2b$12$RJA.K1CLDZ9BER28jbpmhe8bgNFP0xcwInEu81sNj2ckSAD9Mlw9C",
    ),
]

INSERT_SQL = """
INSERT INTO users (id, username, hashed_password, created_at)
VALUES ($1::uuid, $2, $3, now())
ON CONFLICT (username) DO UPDATE SET hashed_password = EXCLUDED.hashed_password
"""

async def main():
    conn = await asyncpg.connect(DB_URL)
    try:
        # Create required tables if they don't exist
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY,
                username VARCHAR(128) UNIQUE NOT NULL,
                hashed_password VARCHAR(256) NOT NULL,
                created_at TIMESTAMP DEFAULT now()
            );
            """
        )

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id UUID PRIMARY KEY,
                type VARCHAR(32) NOT NULL,
                severity VARCHAR(16) NOT NULL,
                message TEXT NOT NULL,
                process_name VARCHAR(128) NOT NULL,
                status VARCHAR(16) NOT NULL DEFAULT 'active',
                metadata JSON,
                created_at TIMESTAMP,
                resolved_at TIMESTAMP WITH TIME ZONE,
                resolved_by VARCHAR(128)
            );
            """
        )

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notification_deliveries (
                id UUID PRIMARY KEY,
                alert_id UUID,
                channel VARCHAR(32) NOT NULL,
                status VARCHAR(32) NOT NULL,
                recipient VARCHAR(256),
                response_reference VARCHAR(128),
                error_message TEXT,
                created_at TIMESTAMP
            );
            """
        )

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id UUID PRIMARY KEY,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                actor VARCHAR(128),
                user_id VARCHAR(128),
                event_type VARCHAR(128),
                component VARCHAR(128),
                input_hash VARCHAR(128),
                algorithm_version VARCHAR(64),
                result_summary JSON,
                metadata JSON,
                ip_address VARCHAR(64)
            );
            """
        )

        # Ensure hypertable exists for audit_events
        try:
            await conn.execute("SELECT create_hypertable('audit_events', 'created_at', if_not_exists => TRUE);")
        except Exception:
            # If TimescaleDB function not available yet, ignore — migrations should handle it.
            pass

        # Add a long-term retention policy (10 years) if function available
        try:
            await conn.execute("SELECT add_retention_policy('audit_events', INTERVAL '3650 days');")
        except Exception:
            pass

        # Insert users
        for uid, username, hashed in USERS:
            await conn.execute(INSERT_SQL, uid, username, hashed)
        print("Prepared DB schema and seeded users into Postgres successfully.")
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
