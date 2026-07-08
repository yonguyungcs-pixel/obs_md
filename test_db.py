import sqlite3
db_path = r"D:\tools\bicv_obsidian\.obsidian\doc-sync\data\sync_state.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("SELECT source_path, status FROM sync_state LIMIT 5")
for row in c.fetchall():
    print(row)
