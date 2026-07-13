from docling.document_converter import DocumentConverter
converter = DocumentConverter()
result = converter.convert(r"D:\DocInbox\sfs\00_PLE\00_OLD\T55-G1(项目暂停)\自定义按键功能_A55项目车机&仪表功能需求表v5.docx")
print(result.document.export_to_markdown()[:1000])
