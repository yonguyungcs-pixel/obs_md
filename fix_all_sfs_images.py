import os
import shutil
from pathlib import Path

inbox_dir = Path(r"D:\DocInbox\sfs")
md_dir = Path(r"D:\tools\bicv_obsidian\3G125\MD_SFS")

count = 0
for root, dirs, files in os.walk(md_dir):
    for file in files:
        if file.endswith(".md"):
            md_path = Path(root) / file
            
            try:
                rel_path = md_path.relative_to(md_dir)
            except ValueError:
                continue
                
            inbox_target = inbox_dir / rel_path.parent
            inbox_media = inbox_target / "media"
            
            if inbox_media.exists() and inbox_media.is_dir():
                target_media = md_path.parent / "media"
                target_media.mkdir(parents=True, exist_ok=True)
                
                for img in inbox_media.iterdir():
                    if img.is_file():
                        dest = target_media / img.name
                        if not dest.exists():
                            shutil.copy2(img, dest)
                            count += 1
                            # print(f"Copied {img.name} to {target_media}")

print(f"Done migrating images for ALL SFS. Total images copied: {count}")
