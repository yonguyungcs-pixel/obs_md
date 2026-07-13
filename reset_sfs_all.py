import sqlite3

db_path = r"D:\tools\bicv_obsidian\.obsidian\doc-sync\data\sync_state.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Reset SFS Word and PDF files
c.execute("DELETE FROM sync_state WHERE source_path LIKE '%sfs%' AND (source_path LIKE '%.doc' OR source_path LIKE '%.docx' OR source_path LIKE '%.pdf')")
conn.commit()
print("Rows deleted:", c.rowcount)
conn.close()
