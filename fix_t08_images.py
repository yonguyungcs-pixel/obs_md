import os
import shutil
import re
from pathlib import Path

inbox_dir = Path(r"D:\DocInbox\sfs\T08-G")
md_dir = Path(r"D:\tools\bicv_obsidian\3G125\MD_SFS\T08-G")

for root, _, files in os.walk(md_dir):
    for file in files:
        if file.endswith(".md"):
            md_path = Path(root) / file
            
            # 找到在 Inbox 中对应的原始文件夹 (可能有稍微不同的层级，但通常就是同级)
            rel_path = md_path.relative_to(md_dir)
            inbox_target = inbox_dir / rel_path.parent
            inbox_media = inbox_target / "media"
            
            if inbox_media.exists() and inbox_media.is_dir():
                # 目标 media 文件夹
                target_media = md_path.parent / "media"
                target_media.mkdir(parents=True, exist_ok=True)
                
                # 拷贝文件
                for img in inbox_media.iterdir():
                    if img.is_file():
                        shutil.copy2(img, target_media / img.name)
                        print(f"Copied {img.name} to {target_media}")

print("Done migrating images.")
