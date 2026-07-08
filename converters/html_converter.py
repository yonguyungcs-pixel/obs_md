"""
converters/html_converter.py — HTML 转 Markdown

主引擎：Pandoc（处理复杂 HTML 结构）
降级：markitdown
"""

import shutil
import subprocess
from pathlib import Path

from loguru import logger

from converters.base import BaseConverter, ConvertResult


class HTMLConverter(BaseConverter):

    @property
    def supported_extensions(self) -> list[str]:
        return ["html", "htm"]

    @property
    def name(self) -> str:
        return "pandoc-html"

    def is_available(self) -> bool:
        if shutil.which("pandoc"):
            return True
        try:
            import markitdown  # noqa: F401
            return True
        except ImportError:
            return False

    def convert(self, source_path: Path, output_dir: Path, config: dict) -> ConvertResult:
        if shutil.which("pandoc"):
            try:
                return self._convert_pandoc(source_path, config)
            except Exception as e:
                logger.warning(f"[HTML] Pandoc 失败，降级 markitdown: {e}")

        try:
            return self._convert_markitdown(source_path)
        except Exception as e:
            return ConvertResult.fail(str(e), self.name)

    def _convert_pandoc(self, source_path: Path, config: dict) -> ConvertResult:
        extra_args = config.get("pandoc", {}).get(
            "extra_args", ["--wrap=none", "--strip-comments"]
        )
        cmd = [
            "pandoc",
            str(source_path),
            "-f", "html",
            "-t", "gfm",
            *extra_args,
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
        logger.info(f"[HTML] Pandoc 转换成功: {source_path.name}")
        return ConvertResult.ok(result.stdout, "pandoc-html")

    def _convert_markitdown(self, source_path: Path) -> ConvertResult:
        from markitdown import MarkItDown
        md = MarkItDown()
        result = md.convert(str(source_path))
        logger.info(f"[HTML] markitdown 转换成功: {source_path.name}")
        return ConvertResult.ok(result.text_content, "markitdown-html")
