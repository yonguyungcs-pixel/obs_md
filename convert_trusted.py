import os
import shutil
import winreg
from pathlib import Path
import win32com.client

inbox_dir = Path(r"D:\DocInbox")
sfs_dir = inbox_dir / "sfs"
backup_dir = Path(r"D:\DocInbox_Backup_Doc")
backup_dir.mkdir(parents=True, exist_ok=True)

# 1. Add Trusted Location to Registry
trusted_loc_key_path = r"Software\Microsoft\Office\16.0\Word\Security\Trusted Locations\LocationDocSync"
try:
    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, trusted_loc_key_path)
    winreg.SetValueEx(key, "Path", 0, winreg.REG_SZ, str(sfs_dir))
    winreg.SetValueEx(key, "AllowSubFolders", 0, winreg.REG_DWORD, 1)
    winreg.SetValueEx(key, "Description", 0, winreg.REG_SZ, "Doc Sync Trusted")
    winreg.CloseKey(key)
    print("Added D:\DocInbox\sfs to Word Trusted Locations.")
except Exception as e:
    print(f"Failed to set Trusted Location: {e}")

# 2. Convert files
doc_files = []
for root, _, files in os.walk(inbox_dir):
    for file in files:
        if file.lower().endswith(".doc") and not file.lower().endswith(".docx") and not file.startswith("~$"):
            doc_files.append(Path(root) / file)

print(f"Found {len(doc_files)} real .doc files.")

if doc_files:
    try:
        word = win32com.client.gencache.EnsureDispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        word.AutomationSecurity = 3
        
        count = 0
        for doc_path in doc_files:
            docx_path = doc_path.with_suffix(".docx")
            print(f"Converting: {doc_path.name}")
            doc = None
            try:
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
        print(f"Successfully converted {count} files.")

# 3. Clean up Trusted Location
try:
    winreg.DeleteKey(winreg.HKEY_CURRENT_USER, trusted_loc_key_path)
    print("Removed Trusted Location from Registry.")
except Exception as e:
    pass
