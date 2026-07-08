import fitz # PyMuPDF
doc = fitz.open(r'D:\DocInbox\ue\88系列\A8E_ADiGO AV_Design Book_设置_v0.2.pdf')
print('Total pages:', len(doc))
print('Text on page 1:')
print(doc[0].get_text())
print('Images on page 1:')
print(doc.get_page_images(0))
