import os
import shutil
import win32com.client
from pathlib import Path
import time

inbox_dir = Path(r"D:\DocInbox\sfs")
backup_dir = Path(r"D:\DocInbox_Backup_Doc\sfs")
backup_dir.mkdir(parents=True, exist_ok=True)

doc_files = []
for root, _, files in os.walk(inbox_dir):
    for file in files:
        if file.lower().endswith(".doc") and not file.lower().endswith(".docx") and not file.startswith("~$"):
            doc_files.append(Path(root) / file)

print(f"Found {len(doc_files)} real .doc files.")

if doc_files:
    try:
        wps = win32com.client.Dispatch("Kwps.Application")
        wps.Visible = False
        
        count = 0
        for doc_path in doc_files:
            docx_path = doc_path.with_suffix(".docx")
            print(f"Converting: {doc_path.name}")
            doc = None
            try:
                doc = wps.Documents.Open(str(doc_path.resolve()))
                doc.SaveAs2(str(docx_path.resolve()), FileFormat=12)
                
                # Move original to backup
                rel_path = doc_path.relative_to(inbox_dir)
                backup_target = backup_dir / rel_path
                backup_target.parent.mkdir(parents=True, exist_ok=True)
                
                # We need to close before move
                doc.Close(SaveChanges=False)
                doc = None
                
                shutil.move(str(doc_path), str(backup_target))
                count += 1
                print(" -> Success")
            except Exception as e:
                print(f" -> Failed: {e}")
            finally:
                if doc:
                    try: doc.Close(SaveChanges=False)
                    except: pass
    finally:
        try: wps.Quit()
        except: pass
        print(f"Successfully converted {count} files.")
