import asyncio
import os
import asyncpg


async def main():
    url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        print("TEST_DATABASE_URL or DATABASE_URL not set")
        return
    conn = await asyncpg.connect(url)
    try:
        print('Searching for audit tables...')
        rows = await conn.fetch("SELECT schemaname, tablename FROM pg_tables WHERE tablename ILIKE 'audit%';")
        if not rows:
            print('No audit tables found')
        else:
            for r in rows:
                print(r['schemaname'], r['tablename'])

        print('\nAlembic versions applied:')
        try:
            rows = await conn.fetch("SELECT * FROM arad_alembic_version;")
            for r in rows:
                print(dict(r))
        except Exception as e:
            print('Could not read arad_alembic_version:', e)

    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(main())
