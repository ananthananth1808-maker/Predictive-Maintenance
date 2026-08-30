"""Direct SQLite inspection."""
import sqlite3

conn = sqlite3.connect('maintenai.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('Tables in database:')
for table in tables:
    tname = table[0]
    print(f'  - {tname}')
    cursor.execute(f'SELECT COUNT(*) FROM {tname}')
    count = cursor.fetchone()[0]
    print(f'    Records: {count}')

conn.close()
