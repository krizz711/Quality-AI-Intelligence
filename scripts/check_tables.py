import asyncio
import os
import asyncpg


async def main():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        print("TEST_DATABASE_URL not set")
        return
    conn = await asyncpg.connect(url)
    try:
        rows = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = current_schema();")
        print([r[0] for r in rows])
    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(main())
