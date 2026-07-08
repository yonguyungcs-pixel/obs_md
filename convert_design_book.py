import fitz
import os
from pathlib import Path

pdf_path = Path(r'D:\DocInbox\ue\88系列\A8E_ADiGO AV_Design Book_设置_v0.2.pdf')
out_md = Path(r'D:\tools\bicv_obsidian\3G125\MD_UE\88系列\A8E_ADiGO AV_Design Book_设置_v0.2.md')
out_assets = out_md.parent / 'assets' / 'images'
out_assets.mkdir(parents=True, exist_ok=True)

doc = fitz.open(pdf_path)
md_lines = [f"# {pdf_path.stem}\n"]

for page_num in range(len(doc)):
    page = doc.load_page(page_num)
    # 设置分辨率（dpi=150 左右即可保持清晰且文件不过大）
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    img_name = f"{pdf_path.stem}_page_{page_num + 1:03d}.png"
    img_path = out_assets / img_name
    pix.save(img_path)
    
    # Obsidian 图片引用格式
    md_lines.append(f"![[assets/images/{img_name}]]\n")

out_md.write_text('\n'.join(md_lines), encoding='utf-8')
print(f"转换完成，共 {len(doc)} 页。")
print(f"MD 已写入: {out_md}")
print(f"图片保存在: {out_assets}")
