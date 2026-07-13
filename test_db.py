import sqlite3
db_path = r"D:\tools\bicv_obsidian\.obsidian\doc-sync\data\sync_state.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("SELECT source_path, converter FROM sync_state WHERE source_path LIKE '%sfs%' AND source_path LIKE '%.docx'")
rows = c.fetchall()
print(f"Total SFS Word files in DB: {len(rows)}")
for r in rows[:5]:
    print(r)
