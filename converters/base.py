"""
converters/base.py — 转换器抽象基类（插件接口）

所有转换器必须继承此类。新增格式时只需创建新的 Converter 文件，
registry.py 会自动发现并注册，无需修改核心代码。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ConvertResult:
    """单次转换的结果。"""
    success: bool
    markdown: str = ""            # 转换后的 Markdown 内容
    converter_name: str = ""      # 使用的转换器标识
    assets: list[Path] = field(default_factory=list)  # 提取出的附件（图片等）
    error: Optional[str] = None   # 失败时的错误信息

    @classmethod
    def ok(cls, markdown: str, converter_name: str, assets: list[Path] | None = None) -> "ConvertResult":
        return cls(success=True, markdown=markdown, converter_name=converter_name, assets=assets or [])

    @classmethod
    def fail(cls, error: str, converter_name: str = "") -> "ConvertResult":
        return cls(success=False, error=error, converter_name=converter_name)


class BaseConverter(ABC):
    """
    所有文档转换器的抽象基类。

    子类只需实现：
      - supported_extensions: 返回支持的扩展名列表（不含点，小写）
      - convert(): 执行实际转换逻辑

    registry.py 会在启动时自动扫描并注册所有 BaseConverter 子类。
    """

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """
        返回此转换器支持的文件扩展名列表（不含点，小写）。
        例如: ["pdf"] 或 ["doc", "docx"]
        """
        ...

    @property
    def name(self) -> str:
        """转换器标识名，默认使用类名，可覆盖。"""
        return self.__class__.__name__.replace("Converter", "").lower()

    @abstractmethod
    def convert(self, source_path: Path, output_dir: Path, config: dict) -> ConvertResult:
        """
        执行文档到 Markdown 的转换。

        Args:
            source_path: 源文件绝对路径
            output_dir:  Markdown 输出目录（附件图片也放在此目录或子目录）
            config:      该转换器的配置字典（来自 config.yaml 对应节）

        Returns:
            ConvertResult 对象
        """
        ...

    def is_available(self) -> bool:
        """
        检查转换器的外部依赖是否已安装（如 pandoc 可执行文件）。
        默认返回 True，有外部依赖的子类应覆盖此方法。
        """
        return True
