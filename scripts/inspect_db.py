import sqlite3
conn = sqlite3.connect('leaklens.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = sorted(r[0] for r in cur.fetchall())
print('TABLES:')
for t in tables:
    print(' -', t)
cur.execute("PRAGMA table_info('user')")
print('\nUSER COLUMNS:')
print(cur.fetchall())
conn.close()
