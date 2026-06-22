import sqlite3
from pathlib import Path

db_path = Path(__file__).resolve().parents[0] / '..' / 'test_users.db'
db_path = db_path.resolve()
print('Checking DB at', db_path)
conn = sqlite3.connect(str(db_path))
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print('TABLES:', tables)
try:
    cur.execute("SELECT username, role FROM users")
    users = cur.fetchall()
    print('USERS:', users)
except Exception as e:
    print('Could not query users:', e)
