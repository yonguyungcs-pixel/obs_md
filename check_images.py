import os
import re
import urllib.parse
from pathlib import Path

base_dir = Path(r"D:\tools\bicv_obsidian\3G125\MD_UE\88系列")
missing_images = []

for root, _, files in os.walk(base_dir):
    for file in files:
        if file.endswith(".md"):
            md_path = Path(root) / file
            content = md_path.read_text(encoding="utf-8")
            
            # Find all image links
            links = re.findall(r'!\[.*?\]\((.*?)\)', content)
            for link in links:
                # Decode URL
                decoded_link = urllib.parse.unquote(link)
                # Resolve relative path
                img_path = (md_path.parent / decoded_link).resolve()
                if not img_path.exists():
                    missing_images.append(f"{md_path.name}: {decoded_link}")

if not missing_images:
    print("All images exist in 88系列!")
else:
    print(f"Found {len(missing_images)} missing images:")
    for m in missing_images:
        print(m)
