import os
import re
import urllib.parse
from pathlib import Path

base_dir = Path(r"D:\tools\bicv_obsidian\3G125\MD_SFS")
missing = []

for root, _, files in os.walk(base_dir):
    for file in files:
        if file.endswith(".md"):
            md_path = Path(root) / file
            if "A21" not in str(md_path) and "58" not in str(md_path):
                continue
            
            content = md_path.read_text(encoding="utf-8")
            links = re.findall(r'!\[.*?\]\((.*?)\)', content)
            for link in links:
                decoded = urllib.parse.unquote(link)
                if decoded.startswith('http') or decoded.startswith('data:'):
                    continue
                img_path = (md_path.parent / decoded).resolve()
                if not img_path.exists():
                    missing.append(f"{md_path.name}: {decoded}")

if not missing:
    print("No missing images in A21/58!")
else:
    print(f"Found {len(missing)} missing images:")
    for m in missing[:20]:
        print(m)
