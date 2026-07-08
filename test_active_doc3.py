import sys
import win32com.client
from pathlib import Path

temp_doc = Path(r"D:\temp_word3.doc")
temp_docx = Path(r"D:\temp_word3.docx")
if temp_docx.exists(): temp_docx.unlink()

try:
    word = win32com.client.gencache.EnsureDispatch("Word.Application")
    word.Visible = False
    word.DisplayAlerts = False
    
    doc = word.Documents.Open(str(temp_doc), ReadOnly=True)
    doc.SaveAs(str(temp_docx), FileFormat=16)
    doc.Close(SaveChanges=False)
    print("Success with SaveAs (Early Binding)!")
except Exception as e:
    import traceback
    print(f"Error: {e}")
    traceback.print_exc()
finally:
    word.Quit()
