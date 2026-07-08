"""
converters/registry.py — 转换器自动注册表

启动时自动扫描 converters/ 目录下所有 BaseConverter 子类并注册。
新增格式只需创建新的 *_converter.py 文件，无需修改此文件。
"""

import importlib
import pkgutil
from pathlib import Path
from typing import Optional

from loguru import logger

from converters.base import BaseConverter


class ConverterRegistry:
    """全局转换器注册表（单例）。"""

    def __init__(self) -> None:
        self._registry: dict[str, BaseConverter] = {}  # ext → converter 实例

    def auto_discover(self, config: dict) -> None:
        """
        自动扫描并导入 converters/ 包下所有模块，
        注册所有 BaseConverter 子类实例。
        """
        converters_pkg_dir = Path(__file__).parent
        package_name = "converters"

        for _, module_name, _ in pkgutil.iter_modules([str(converters_pkg_dir)]):
            if module_name in ("base", "registry"):
                continue
            try:
                mod = importlib.import_module(f"{package_name}.{module_name}")
            except ImportError as e:
                logger.warning(f"[Registry] 跳过模块 {module_name}: {e}")
                continue

            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseConverter)
                    and attr is not BaseConverter
                ):
                    try:
                        instance = attr()
                        self._register(instance)
                    except Exception as e:
                        logger.error(f"[Registry] 实例化 {attr_name} 失败: {e}")

        logger.info(
            f"[Registry] 注册完成，支持扩展名: {sorted(self._registry.keys())}"
        )

    def _register(self, converter: BaseConverter) -> None:
        if not converter.is_available():
            logger.warning(
                f"[Registry] {converter.name} 依赖未满足，跳过注册: "
                f"{converter.supported_extensions}"
            )
            return
        for ext in converter.supported_extensions:
            ext = ext.lower().lstrip(".")
            if ext in self._registry:
                logger.warning(
                    f"[Registry] 扩展名 '{ext}' 已被 "
                    f"{self._registry[ext].name} 注册，"
                    f"{converter.name} 将覆盖"
                )
            self._registry[ext] = converter
            logger.debug(f"[Registry] {ext!r} → {converter.name}")

    def get(self, ext: str) -> Optional[BaseConverter]:
        """根据扩展名获取对应转换器，不存在返回 None。"""
        return self._registry.get(ext.lower().lstrip("."))

    def supported_extensions(self) -> set[str]:
        return set(self._registry.keys())

    def list_all(self) -> dict[str, str]:
        """返回 {ext: converter_name} 映射，用于状态输出。"""
        return {ext: conv.name for ext, conv in self._registry.items()}


# 全局单例
registry = ConverterRegistry()
