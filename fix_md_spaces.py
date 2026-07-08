import os
import urllib.parse
import re
from pathlib import Path

base_dir = Path(r"D:\tools\bicv_obsidian\3G125\MD_UE")
for root, _, files in os.walk(base_dir):
    for file in files:
        if file.endswith(".md"):
            filepath = Path(root) / file
            content = filepath.read_text(encoding="utf-8")
            
            # Find all ![...](...) links
            def replace_link(match):
                alt_text = match.group(1)
                img_path = match.group(2)
                # URL encode the image path
                encoded_path = urllib.parse.quote(img_path)
                return f"![{alt_text}]({encoded_path})"
            
            new_content = re.sub(r'!\[(.*?)\]\((.*?)\)', replace_link, content)
            
            if new_content != content:
                filepath.write_text(new_content, encoding="utf-8")
                print(f"Fixed spaces/encoding in {file}")
