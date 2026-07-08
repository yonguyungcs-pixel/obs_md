import os
import shutil
from pathlib import Path
import win32com.client
import time

inbox_dir = Path(r"D:\DocInbox")
backup_dir = Path(r"D:\DocInbox_Backup_Doc")

backup_dir.mkdir(parents=True, exist_ok=True)

doc_files = []
for root, _, files in os.walk(inbox_dir):
    for file in files:
        if file.lower().endswith(".doc") and not file.lower().endswith(".docx"):
            doc_files.append(Path(root) / file)

if not doc_files:
    print("No .doc files found.")
else:
    print(f"Found {len(doc_files)} .doc files.")
    try:
        word = win32com.client.gencache.EnsureDispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0 # wdAlertsNone
        # 3 = msoAutomationSecurityForceDisable
        word.AutomationSecurity = 3
        
        count = 0
        for doc_path in doc_files:
            docx_path = doc_path.with_suffix(".docx")
            print(f"Converting: {doc_path.name}")
            doc = None
            try:
                # Open with minimal interactions
                doc = word.Documents.Open(str(doc_path.resolve()), ConfirmConversions=False, ReadOnly=True, AddToRecentFiles=False, Visible=False)
                doc.SaveAs(str(docx_path.resolve()), FileFormat=16)
                
                # Move original to backup
                rel_path = doc_path.relative_to(inbox_dir)
                backup_target = backup_dir / rel_path
                backup_target.parent.mkdir(parents=True, exist_ok=True)
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
        try: word.Quit()
        except: pass
        print(f"Done! Converted {count} files.")
