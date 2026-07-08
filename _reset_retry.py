import sqlite3, yaml, sys
sys.path.insert(0, ".")
cfg = yaml.safe_load(open("config.yaml", encoding="utf-8"))
db_path = cfg["paths"]["state_db"]
conn = sqlite3.connect(db_path)
conn.execute("UPDATE sync_state SET retry_count=0, status='failed'")
conn.commit()
rows = conn.execute("SELECT source_path, status, retry_count FROM sync_state").fetchall()
for r in rows:
    print(r)
conn.close()
print("done")
