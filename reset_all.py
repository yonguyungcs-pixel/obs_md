import sqlite3
db_path = r"D:\tools\bicv_obsidian\.obsidian\doc-sync\data\sync_state.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("DELETE FROM sync_state WHERE source_path LIKE '%fl%' OR source_path LIKE '%sfs%' OR source_path LIKE '%ue%'")
conn.commit()
print("Rows deleted:", c.rowcount)
conn.close()
