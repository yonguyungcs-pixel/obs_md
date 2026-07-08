import sys
import win32com.client
from pathlib import Path
import subprocess

doc_path = Path(r"D:\DocInbox\sfs\T55-G2\方控\自定义按键功能_A5X项目车机&仪表功能需求表v0.doc")
temp_doc = Path(r"D:\temp_word.doc")
temp_docx = Path(r"D:\temp_word.docx")

if temp_doc.exists(): temp_doc.unlink()
if temp_docx.exists(): temp_docx.unlink()

# Write bytes to strip MotW
with open(doc_path, 'rb') as f_in:
    with open(temp_doc, 'wb') as f_out:
        f_out.write(f_in.read())

try:
    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    word.DisplayAlerts = False
    
    doc = word.Documents.Open(str(temp_doc), ReadOnly=True)
    doc.SaveAs2(str(temp_docx), FileFormat=16)
    doc.Close(SaveChanges=False)
    print("Success after stripping MotW!")
except Exception as e:
    import traceback
    print(f"Error: {e}")
    traceback.print_exc()
finally:
    word.Quit()
