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
        engine = config.get("word", {}).get("engine", "pandoc")
        
        if engine == "docling":
            try:
                return self._convert_docling(source_path)
            except ImportError:
                logger.warning(f"[Word] Docling 未安装，降级尝试 Pandoc")
            except Exception as e:
                logger.warning(f"[Word] Docling 失败，降级尝试 Pandoc: {e}")
        
        if shutil.which("pandoc") and engine != "markitdown":
            try:
                return self._convert_pandoc(source_path, output_dir, config)
            except Exception as e:
                logger.warning(f"[Word] Pandoc 失败，降级: {e}")

        # 3. 降级 markitdown
        try:
            return self._convert_markitdown(source_path)
        except Exception as e:
            return ConvertResult.fail(str(e), self.name)

    def _convert_pandoc(self, source_path: Path, output_dir: Path, config: dict) -> ConvertResult:
        extra_args = config.get("pandoc", {}).get("extra_args", ["--wrap=none"])
        
        # 使用相对路径，避免 Pandoc 输出绝对路径导致 Obsidian 无法识别或因过长而被截断换行
        # 将 cwd 设为 output_dir，这样 pandoc 输出的内容就是基于当前 markdown 文件的相对路径
        media_dir_rel = f"assets/{source_path.stem}"
        
        cmd = [
            "pandoc",
            str(source_path),
            "-f", "docx",
            "-t", "gfm",          # GitHub Flavored Markdown
            "--extract-media", media_dir_rel,
            *extra_args,
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(output_dir),
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
            
        # 对生成的 markdown 里的图片路径进行 URL 编码（处理空格问题），否则部分标准 Markdown 阅读器会断行
        import re
        import urllib.parse
        md_text = result.stdout
        def url_encode_path(match):
            alt_text = match.group(1)
            raw_path = match.group(2)
            # URL encode 空格等特殊字符
            parts = raw_path.split('/')
            encoded_parts = [urllib.parse.quote(p) for p in parts]
            return f"![{alt_text}](" + "/".join(encoded_parts) + ")"
        
        md_text = re.sub(r'!\[(.*?)\]\(([^)]+)\)', url_encode_path, md_text)
        
        logger.info(f"[Word] Pandoc 转换成功: {source_path.name}")
        return ConvertResult.ok(md_text, "pandoc-word")

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
