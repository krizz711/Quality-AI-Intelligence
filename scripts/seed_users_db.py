import sqlite3
from pathlib import Path

seed_env = None
import os
seed_env = os.environ.get("SEED_DB_PATH")
if seed_env:
    db_path = Path(seed_env).resolve()
else:
    db_path = Path(__file__).resolve().parents[0] / '..' / 'test_users.db'
    db_path = db_path.resolve()
print('Seeding DB at', db_path)

conn = sqlite3.connect(str(db_path))
cur = conn.cursor()

# Create users table if it doesn't exist (simple schema matching alembic)
cur.execute('''
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

users = [
    ('88bfcab2-7dde-4de9-938a-b1f457b68845', 'admin', '$2b$12$RJA.K1CLDZ9BER28jbpmhe8bgNFP0xcwInEu81sNj2ckSAD9Mlw9C', 'admin'),
    ('151d6469-dfd7-45e7-a045-f67c905c42ad', 'quality_engineer', '$2b$12$wEz9U18MOvVJguiiVM69peOIMMjy0NDJulcByMP0WTpjlulj6v2Fm', 'quality_engineer'),
]

for u in users:
    try:
        cur.execute(
            "INSERT OR IGNORE INTO users (id, username, hashed_password, role) VALUES (?, ?, ?, ?)",
            u,
        )
    except Exception as e:
        print('Error inserting', u[1], e)

conn.commit()
print('Seed complete')
