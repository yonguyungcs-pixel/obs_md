import sqlite3
import time

db_path = r"D:\tools\bicv_obsidian\.obsidian\doc-sync\data\sync_state.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Get count before
c.execute("SELECT COUNT(*) FROM sync_state WHERE source_path LIKE '%sfs%' AND (source_path LIKE '%.doc' OR source_path LIKE '%.docx')")
count = c.fetchone()[0]
print(f"Found {count} Word files in SFS to reset.")

# Delete to force reconversion
c.execute("DELETE FROM sync_state WHERE source_path LIKE '%sfs%' AND (source_path LIKE '%.doc' OR source_path LIKE '%.docx')")
conn.commit()
conn.close()
print("Reset complete.")
