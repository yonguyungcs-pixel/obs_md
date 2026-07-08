import os
import shutil
from pathlib import Path
import win32com.client

inbox_dir = Path(r"D:\DocInbox")
backup_dir = Path(r"D:\DocInbox_Backup_Doc")

backup_dir.mkdir(parents=True, exist_ok=True)

# Find all .doc files (ignoring .docx)
doc_files = []
for root, _, files in os.walk(inbox_dir):
    for file in files:
        if file.lower().endswith(".doc") and not file.lower().endswith(".docx"):
            doc_files.append(Path(root) / file)

if not doc_files:
    print("No .doc files found to convert.")
else:
    print(f"Found {len(doc_files)} .doc files. Starting conversion via Word COM...")
    try:
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = False
        
        count = 0
        for doc_path in doc_files:
            docx_path = doc_path.with_suffix(".docx")
            try:
                print(f"Converting: {doc_path.name}")
                doc = word.Documents.Open(str(doc_path.resolve()))
                # 16 is wdFormatXMLDocument (docx)
                doc.SaveAs2(str(docx_path.resolve()), FileFormat=16)
                doc.Close(SaveChanges=False)
                
                # Move original .doc to backup
                rel_path = doc_path.relative_to(inbox_dir)
                backup_target = backup_dir / rel_path
                backup_target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(doc_path), str(backup_target))
                count += 1
            except Exception as e:
                print(f"Failed to convert {doc_path.name}: {e}")
                
    finally:
        word.Quit()
        print(f"Successfully converted {count} / {len(doc_files)} files to .docx.")
