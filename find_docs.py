import os
from pathlib import Path

inbox_dir = Path(r"D:\DocInbox")
for root, _, files in os.walk(inbox_dir):
    for file in files:
        if file.lower().endswith(".doc") and not file.lower().endswith(".docx"):
            print(Path(root) / file)
