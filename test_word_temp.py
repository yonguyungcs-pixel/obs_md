import sys
import shutil
import win32com.client
from pathlib import Path

doc_path = Path(r"D:\DocInbox\sfs\T08-G\设置\00_OLD\BCM\自定义按键功能_A5X项目车机&仪表功能需求表v0.doc")
temp_doc = Path(r"D:\temp_word.doc")
temp_docx = Path(r"D:\temp_word.docx")

if temp_doc.exists(): temp_doc.unlink()
if temp_docx.exists(): temp_docx.unlink()

shutil.copy2(doc_path, temp_doc)

try:
    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    word.DisplayAlerts = False
    
    doc = word.Documents.Open(str(temp_doc), ReadOnly=True)
    doc.SaveAs2(str(temp_docx), FileFormat=16)
    doc.Close(SaveChanges=False)
    print("Success converting in temp dir!")
except Exception as e:
    print(f"Error: {e}")
finally:
    word.Quit()
