import sqlite3
from pathlib import Path

db_path = Path(__file__).resolve().parents[0] / '..' / 'test_users.db'
db_path = db_path.resolve()
print('DB:', db_path)
conn = sqlite3.connect(str(db_path))
cur = conn.cursor()
cur.execute("SELECT username, hashed_password FROM users")
rows = cur.fetchall()
for r in rows:
    username, hashed = r
    print(username, 'len=', len(hashed))
    print('hash:', hashed)
