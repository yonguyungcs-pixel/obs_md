"""
converters/pdf_converter.py — PDF 转 Markdown（Docling 引擎）

使用 IBM Docling 进行布局感知的高质量 PDF 转换，支持：
- 表格结构保留
- 图片提取
- 多栏布局识别
- 扫描件 OCR（需 GPU 可选）

回退方案：如果 Docling 未安装，自动降级为 markitdown。
"""

from pathlib import Path

from loguru import logger

from converters.base import BaseConverter, ConvertResult


class PDFConverter(BaseConverter):
    """PDF → Markdown，将每一页渲染为高清图片并嵌入 Markdown。"""

    @property
    def supported_extensions(self) -> list[str]:
        return ["pdf"]

    @property
    def name(self) -> str:
        return "pymupdf-pdf"

    def is_available(self) -> bool:
        try:
            import fitz  # noqa: F401
            return True
        except ImportError:
            return False

    def convert(self, source_path: Path, output_dir: Path, config: dict) -> ConvertResult:
        try:
            return self._convert_pymupdf(source_path, output_dir, config)
        except Exception as e:
            logger.error(f"[PDF] PyMuPDF 转换失败: {e}")
            return ConvertResult.fail(str(e), self.name)

    def _convert_pymupdf(self, source_path: Path, output_dir: Path, config: dict) -> ConvertResult:
        import fitz

        images_subdir = config.get("images_dir", "assets/images")
        img_dir = output_dir / images_subdir
        
        try:
            doc = fitz.open(str(source_path))
        except Exception as e:
            return ConvertResult.fail(f"无法打开 PDF: {e}", self.name)

        md_lines = [f"# {source_path.stem}\n"]
        assets: list[Path] = []
        import urllib.parse

        if len(doc) > 0:
            img_dir.mkdir(parents=True, exist_ok=True)

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            # 缩放矩阵 2.0，保持较高清晰度 (大约 144 DPI)
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            
            img_name = f"{source_path.stem}_page_{page_num + 1:03d}.png"
            img_path = img_dir / img_name
            
            try:
                pix.save(str(img_path))
                assets.append(img_path)
                # 使用标准 Markdown 语法，并对含有空格的路径进行 URL 编码，完全兼容 Typora
                encoded_img_path = urllib.parse.quote(f"{images_subdir}/{img_name}")
                md_lines.append(f"![Page {page_num+1}]({encoded_img_path})\n")
            except Exception as e:
                logger.warning(f"[PDF] 图片 {page_num+1} 保存失败: {e}")

        markdown = "\n".join(md_lines)
        logger.info(f"[PDF] 转换完成，共 {len(doc)} 页: {source_path.name}")
        return ConvertResult.ok(markdown, self.name, assets)
