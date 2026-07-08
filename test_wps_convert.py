import win32com.client
from pathlib import Path

doc_path = Path(r"D:\DocInbox\sfs\00_PLE\00_OLD\T55-G1(项目暂停)\T55-G1 节点交互文档0430\A5X 项目换挡指示灯功能需求表V0(新增1.5T)-20230719.doc")
docx_path = Path(r"D:\temp_wps.docx")
if docx_path.exists(): docx_path.unlink()

try:
    wps = win32com.client.Dispatch("Kwps.Application")
    wps.Visible = False
    doc = wps.Documents.Open(str(doc_path))
    doc.SaveAs2(str(docx_path), FileFormat=12) # 12 or 16 usually works for docx
    doc.Close()
    print("Success! Created:", docx_path.exists())
except Exception as e:
    import traceback
    print("Error:", e)
    traceback.print_exc()
finally:
    wps.Quit()
