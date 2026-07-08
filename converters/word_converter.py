"""
converters/word_converter.py — Word (.doc/.docx) 转 Markdown

主引擎：Pandoc（保留格式最完整）
降级：Docling → markitdown
"""

import shutil
import subprocess
from pathlib import Path

from loguru import logger

from converters.base import BaseConverter, ConvertResult


class WordConverter(BaseConverter):

    @property
    def supported_extensions(self) -> list[str]:
        return ["doc", "docx"]

    @property
    def name(self) -> str:
        return "pandoc-word"

    def is_available(self) -> bool:
        if shutil.which("pandoc"):
            return True
        try:
            import docling  # noqa: F401
            return True
        except ImportError:
            pass
        try:
            import markitdown  # noqa: F401
            return True
        except ImportError:
            return False

    def convert(self, source_path: Path, output_dir: Path, config: dict) -> ConvertResult:
        # 1. 尝试 Pandoc
        if shutil.which("pandoc"):
            try:
                return self._convert_pandoc(source_path, output_dir, config)
            except Exception as e:
                logger.warning(f"[Word] Pandoc 失败，降级: {e}")

        # 2. 降级 Docling
        try:
            return self._convert_docling(source_path)
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"[Word] Docling 失败，降级 markitdown: {e}")

        # 3. 降级 markitdown
        try:
            return self._convert_markitdown(source_path)
        except Exception as e:
            return ConvertResult.fail(str(e), self.name)

    def _convert_pandoc(self, source_path: Path, output_dir: Path, config: dict) -> ConvertResult:
        extra_args = config.get("pandoc", {}).get("extra_args", ["--wrap=none"])
        
        # 将图片提取到 output_dir/assets/{stem} 中，避免不同文档的图片冲突
        media_dir = output_dir / "assets" / source_path.stem
        
        cmd = [
            "pandoc",
            str(source_path),
            "-f", "docx",
            "-t", "gfm",          # GitHub Flavored Markdown
            "--extract-media", str(media_dir),
            *extra_args,
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(source_path.parent),
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
        logger.info(f"[Word] Pandoc 转换成功: {source_path.name}")
        return ConvertResult.ok(result.stdout, "pandoc-word")

    def _convert_docling(self, source_path: Path) -> ConvertResult:
        from docling.document_converter import DocumentConverter
        converter = DocumentConverter()
        result = converter.convert(str(source_path))
        markdown = result.document.export_to_markdown()
        logger.info(f"[Word] Docling 转换成功: {source_path.name}")
        return ConvertResult.ok(markdown, "docling-word")

    def _convert_markitdown(self, source_path: Path) -> ConvertResult:
        from markitdown import MarkItDown
        md = MarkItDown()
        result = md.convert(str(source_path))
        logger.info(f"[Word] markitdown 转换成功: {source_path.name}")
        return ConvertResult.ok(result.text_content, "markitdown-word")
