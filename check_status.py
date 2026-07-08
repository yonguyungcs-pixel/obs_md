import os
import sqlite3
import yaml
from pathlib import Path

inbox_dir = Path(r"D:\DocInbox\ue")
db_path = Path(r"D:\tools\bicv_obsidian\.obsidian\doc-sync\data\sync_state.db")
config_path = Path(r"D:\tools\bicv_obsidian\.obsidian\doc-sync\config.yaml")

# 1. 获取白名单关键词
with open(config_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)
keywords = config['inbox_path_rules'][0]['include_keywords']

# 2. 扫描 Inbox 所有相关文件
target_files = []
for root, _, files in os.walk(inbox_dir):
    for file in files:
        if file.lower().endswith('.pdf'):
            if any(kw in file for kw in keywords) or any(kw in root for kw in keywords):
                target_files.append(Path(root) / file)

# 3. 查询数据库状态
completed_files = set()
if db_path.exists():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT source_path FROM sync_state WHERE status='success'")
    for row in c.fetchall():
        completed_files.add(Path(row[0]))
    conn.close()

# 4. 分类统计 (按项目分类)
projects = {}
for f in target_files:
    # 提取项目名 (例如 29系列, T55-G2 等)
    try:
        project_name = f.relative_to(inbox_dir).parts[0]
    except:
        project_name = "其他"
        
    if project_name not in projects:
        projects[project_name] = {"done": [], "pending": []}
        
    if f in completed_files:
        projects[project_name]["done"].append(f.name)
    else:
        projects[project_name]["pending"].append(f.name)

# 5. 打印结果
for proj, data in projects.items():
    print(f"\n[{proj}]")
    if data["done"]:
        print(f"  ✅ 已完成 ({len(data['done'])}个):")
        for f in data["done"]:
            print(f"    - {f}")
    if data["pending"]:
        print(f"  ⏳ 待执行/执行中 ({len(data['pending'])}个):")
        for f in data["pending"]:
            print(f"    - {f}")
