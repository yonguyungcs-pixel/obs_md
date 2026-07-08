import sys
import win32com.client
from pathlib import Path

doc_path = Path(r"D:\DocInbox\sfs\T08-G\设置\00_OLD\BCM\自定义按键功能_A5X项目车机&仪表功能需求表v0.doc")

try:
    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    word.DisplayAlerts = False
    
    abs_path = str(doc_path.absolute())
    print(f"Opening absolute path: {abs_path}")
    doc = word.Documents.Open(abs_path, ReadOnly=True)
    
    docx_path = doc_path.with_suffix(".test.docx")
    print(f"Saving to: {docx_path}")
    doc.SaveAs2(str(docx_path.absolute()), FileFormat=16)
    doc.Close(SaveChanges=False)
    print("Success!")
except Exception as e:
    print(f"Error: {e}")
finally:
    word.Quit()
