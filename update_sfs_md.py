import os
import sqlite3
import yaml
from pathlib import Path

inbox_dir = Path(r"D:\DocInbox\sfs")
db_path = Path(r"D:\tools\bicv_obsidian\.obsidian\doc-sync\data\sync_state.db")
md_path = Path(r"D:\tools\bicv_obsidian\3G125\MD_SFS\00_SFS转换进度与自动同步说明.md")

# SFS 没有在 config.yaml 设置 include_keywords，所有 sfs 下的文档默认全量转换 (在 sync_daemon.py 中配置的)
target_files = []
for root, _, files in os.walk(inbox_dir):
    for file in files:
        if file.lower().endswith(('.pdf', '.docx', '.doc')):
            target_files.append(Path(root) / file)

completed_files = set()
if db_path.exists():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT source_path FROM sync_state WHERE status='ok'")
    for row in c.fetchall():
        completed_files.add(Path(row[0]))
    conn.close()

projects = {}
for f in target_files:
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

output = []
output.append("# SFS 文档转换与同步状态追踪\n")
output.append("本文档用于记录 MD_SFS (需求规范) 目录下的自动转换状态。")
output.append("所有放入 Inbox/sfs 目录下的 Word/PDF 等文档，都会被自动处理。")
output.append("\n## 📊 各项目详细进度\n")
output.append("> 数据由后台实时统计生成\n")

for proj, data in sorted(projects.items()):
    output.append(f"### {proj}")
    
    if data["done"]:
        output.append(f"**✅ 已完成 ({len(data['done'])}个)**")
        for f in sorted(data["done"]):
            output.append(f"- {f}")
    
    if data["pending"]:
        output.append(f"**⏳ 待执行/执行中 ({len(data['pending'])}个)**")
        for f in sorted(data["pending"]):
            output.append(f"- {f}")
    
    output.append("")

report = "\n".join(output)

md_path.parent.mkdir(parents=True, exist_ok=True)
md_path.write_text(report, encoding='utf-8')
print("SFS 文档更新成功。")
