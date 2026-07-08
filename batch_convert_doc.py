import os
import shutil
import time
from pathlib import Path
import win32com.client

inbox_dir = Path(r"D:\DocInbox")
backup_dir = Path(r"D:\DocInbox_Backup_Doc")

backup_dir.mkdir(parents=True, exist_ok=True)

# Find all .doc files (ignoring .docx and lock files)
doc_files = []
for root, _, files in os.walk(inbox_dir):
    for file in files:
        if file.lower().endswith(".doc") and not file.lower().endswith(".docx") and not file.startswith("~$"):
            doc_files.append(Path(root) / file)

if not doc_files:
    print("No .doc files found to convert.")
else:
    print(f"Found {len(doc_files)} .doc files. Starting conversion...")
    
    app_name = "Kwps.Application"
    app = None
    try:
        # Try WPS Office first (better compatibility with old .doc files, avoids Microsoft Word's Protected View blocks)
        app = win32com.client.Dispatch("Kwps.Application")
        print("Using WPS Office (Kwps.Application) for conversion...")
    except Exception as e1:
        print("WPS Office (Kwps.Application) not found or failed, falling back to Word...")
        try:
            app = win32com.client.Dispatch("Word.Application")
            app_name = "Word.Application"
            print("Using Microsoft Word (Word.Application) for conversion...")
        except Exception as e2:
            print("Both WPS Office and Microsoft Word failed to start. Cannot convert.")
            exit(1)

    if app:
        try:
            app.Visible = False
            if app_name == "Word.Application":
                app.DisplayAlerts = 0
                app.AutomationSecurity = 3
                
            count = 0
            for doc_path in doc_files:
                docx_path = doc_path.with_suffix(".docx")
                try:
                    print(f"Converting: {doc_path.name}")
                    doc = app.Documents.Open(str(doc_path.resolve()))
                    # FileFormat 12 and 16 both generally save as docx
                    format_code = 12 if app_name == "Kwps.Application" else 16
                    doc.SaveAs2(str(docx_path.resolve()), FileFormat=format_code)
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
            try:
                app.Quit()
            except:
                pass
            print(f"Successfully converted {count} / {len(doc_files)} files to .docx.")
