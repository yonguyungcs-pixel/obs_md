import subprocess
from pathlib import Path

source_path = Path(r"D:\DocInbox\sfs\00_PLE\00_OLD\T55-G1(项目暂停)\自定义按键功能_A55项目车机&仪表功能需求表v5.docx")
output_dir = Path(r"D:\tools\bicv_obsidian\3G125\MD_SFS\00_PLE\00_OLD\T55-G1(项目暂停)")

media_dir_rel = f"assets/{source_path.stem}"

cmd = [
    "pandoc",
    str(source_path),
    "-f", "docx",
    "-t", "gfm",
    "--extract-media", media_dir_rel,
    "--wrap=none"
]
result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    encoding="utf-8",
    cwd=str(output_dir),
)

import re
lines = result.stdout.split('\n')
for line in lines:
    if "![" in line:
        print(line)
