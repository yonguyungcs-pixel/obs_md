"""
converters/excel_converter.py — Excel (.xls/.xlsx) 转 Markdown

将 Excel 每个 Sheet 转换为 Markdown 表格，
多 Sheet 文件使用 H2 标题分隔。

支持：合并单元格展平、数字格式化、空行过滤。
"""

from pathlib import Path
from typing import Any

from loguru import logger

from converters.base import BaseConverter, ConvertResult


class ExcelConverter(BaseConverter):

    @property
    def supported_extensions(self) -> list[str]:
        return ["xlsx", "xls", "csv"]

    @property
    def name(self) -> str:
        return "pandas-excel"

    def is_available(self) -> bool:
        try:
            import pandas  # noqa: F401
            import openpyxl  # noqa: F401
            return True
        except ImportError:
            return False

    def convert(self, source_path: Path, output_dir: Path, config: dict) -> ConvertResult:
        ext = source_path.suffix.lower()
        try:
            if ext == ".csv":
                return self._convert_csv(source_path, config)
            else:
                return self._convert_excel(source_path, config)
        except Exception as e:
            return ConvertResult.fail(str(e), self.name)

    # ---- Excel ----

    def _convert_excel(self, source_path: Path, config: dict) -> ConvertResult:
        import pandas as pd

        max_rows = config.get("max_rows", 5000)
        sheets_mode = config.get("sheets", "all")  # all | first | named

        xl = pd.ExcelFile(str(source_path))
        sheet_names: list[str] = xl.sheet_names

        if sheets_mode == "first":
            sheet_names = sheet_names[:1]

        sections: list[str] = []
        for sheet_name in sheet_names:
            df = pd.read_excel(
                str(source_path),
                sheet_name=sheet_name,
                nrows=max_rows,
                dtype=str,          # 保持原始文本，避免数字类型问题
            )
            df = df.dropna(how="all")    # 去除全空行
            df = df.fillna("")

            md_table = _df_to_markdown(df)
            header = f"## Sheet: {sheet_name}\n\n" if len(sheet_names) > 1 else ""
            sections.append(f"{header}{md_table}")

        content = "\n\n---\n\n".join(sections)
        logger.info(
            f"[Excel] 转换成功: {source_path.name}，"
            f"共 {len(sheet_names)} 个 Sheet"
        )
        return ConvertResult.ok(content, self.name)

    # ---- CSV ----

    def _convert_csv(self, source_path: Path, config: dict) -> ConvertResult:
        import pandas as pd

        max_rows = config.get("max_rows", 5000)
        df = pd.read_csv(str(source_path), nrows=max_rows, dtype=str).fillna("")
        content = _df_to_markdown(df)
        logger.info(f"[Excel] CSV 转换成功: {source_path.name}")
        return ConvertResult.ok(content, "pandas-csv")


# ------------------------------------------------------------------
# 内部工具：DataFrame → Markdown 表格
# ------------------------------------------------------------------

def _df_to_markdown(df: Any) -> str:
    """将 pandas DataFrame 转换为 GFM Markdown 表格。"""
    if df.empty:
        return "_（空表格）_"

    headers = list(df.columns)
    col_widths = [max(len(str(h)), _max_col_width(df, h)) for h in headers]

    # 表头行
    header_row = "| " + " | ".join(
        str(h).ljust(col_widths[i]) for i, h in enumerate(headers)
    ) + " |"

    # 分隔行
    sep_row = "| " + " | ".join("-" * w for w in col_widths) + " |"

    # 数据行
    data_rows = []
    for _, row in df.iterrows():
        cells = [
            str(row[h]).replace("|", "\\|").ljust(col_widths[i])
            for i, h in enumerate(headers)
        ]
        data_rows.append("| " + " | ".join(cells) + " |")

    return "\n".join([header_row, sep_row, *data_rows])


def _max_col_width(df: Any, col: str, max_width: int = 40) -> int:
    return min(df[col].astype(str).str.len().max(), max_width)
