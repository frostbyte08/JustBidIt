import sqlite3

conn = sqlite3.connect('procurement.db')
c = conn.cursor()

c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
print('Tables:', [t[0] for t in tables])
print()

for table in ['users', 'tenders', 'company_profiles']:
    try:
        c.execute(f'SELECT COUNT(*) FROM {table}')
        count = c.fetchone()[0]
        print(f'{table}: {count} records')
        if count > 0:
            c.execute(f'SELECT * FROM {table} LIMIT 1')
            print(f'  Sample: {c.fetchone()}')
    except Exception as e:
        print(f'{table}: Error - {e}')

conn.close()
