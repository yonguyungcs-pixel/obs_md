import sys
import win32com.client
from pathlib import Path

temp_doc = Path(r"D:\temp_word3.doc")

try:
    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    word.DisplayAlerts = False
    
    print("Opening doc...")
    word.Documents.Open(str(temp_doc), ReadOnly=True)
    
    print(f"ActiveDocument Name: {word.ActiveDocument.Name}")
    
except Exception as e:
    import traceback
    print(f"Error: {e}")
    traceback.print_exc()
finally:
    word.Quit()
