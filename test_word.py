import sys
import traceback
import win32com.client
from pathlib import Path

doc_path = Path(r"D:\DocInbox\sfs\T08-G\设置\00_OLD\BCM\自定义按键功能_A5X项目车机&仪表功能需求表v0.doc")

try:
    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    word.DisplayAlerts = False
    print(f"Opening: {doc_path}")
    doc = word.Documents.Open(str(doc_path.resolve()), ReadOnly=True)
    
    docx_path = doc_path.with_suffix(".test.docx")
    print(f"Saving to: {docx_path}")
    doc.SaveAs2(str(docx_path.resolve()), FileFormat=16)
    doc.Close(SaveChanges=False)
    print("Success!")
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
finally:
    word.Quit()
