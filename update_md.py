import os
import sqlite3
import yaml
from pathlib import Path

inbox_dir = Path(r"D:\DocInbox\ue")
db_path = Path(r"D:\tools\bicv_obsidian\.obsidian\doc-sync\data\sync_state.db")
config_path = Path(r"D:\tools\bicv_obsidian\.obsidian\doc-sync\config.yaml")
md_path = Path(r"D:\tools\bicv_obsidian\3G125\MD_UE\00_转换进度与自动同步说明.md")

with open(config_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)
keywords = config['inbox_path_rules'][0]['include_keywords']

target_files = []
for root, _, files in os.walk(inbox_dir):
    for file in files:
        if file.lower().endswith('.pdf'):
            if any(kw in file for kw in keywords) or any(kw in root for kw in keywords):
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

# Update MD file
content = md_path.read_text(encoding='utf-8')
if "## 📊 各项目详细进度" in content:
    content = content[:content.find("## 📊 各项目详细进度")]

content += "## 📊 各项目详细进度\n\n"
content += "> 数据由后台实时统计生成\n\n"
content += report

md_path.write_text(content, encoding='utf-8')
print("文档更新成功。")
print(report)
