from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
import sys

source_path = r'D:\DocInbox\ue\88系列\A8E_ADiGO AV_Design Book_设置_v0.2.pdf'

options = PdfPipelineOptions()
options.do_ocr = False
options.generate_picture_images = True

converter = DocumentConverter(
    format_options={'pdf': PdfFormatOption(pipeline_options=options)}
)

print('Starting conversion...')
try:
    result = converter.convert(source_path)
    md = result.document.export_to_markdown()
    print('Length of Markdown:', len(md))
    print('Preview:')
    print(md[:500])
except Exception as e:
    print('Error:', e)
