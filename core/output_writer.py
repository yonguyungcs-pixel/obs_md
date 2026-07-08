"""
core/output_writer.py — Markdown 输出写入器

负责将转换后的 Markdown 内容写入 Obsidian Vault，
并自动注入/更新 YAML Frontmatter。
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import frontmatter
from loguru import logger


def write_markdown(
    content: str,
    output_path: Path,
    frontmatter_data: dict,
    overwrite: bool = True,
) -> None:
    """
    将 Markdown 内容写入文件，自动合并 Frontmatter。

    如果文件已存在且 overwrite=True，更新内容但保留用户手动添加的 Frontmatter 字段。
    如果文件已存在且 overwrite=False，跳过写入。

    Args:
        content:          纯 Markdown 正文
        output_path:      输出文件路径
        frontmatter_data: 要写入的 Frontmatter 字典
        overwrite:        是否覆盖已有文件
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 读取已有文件的 Frontmatter（保留用户字段）
    existing_meta: dict = {}
    if output_path.exists() and overwrite:
        try:
            post = frontmatter.load(str(output_path))
            existing_meta = dict(post.metadata)
        except Exception as e:
            logger.warning(f"[Writer] 读取已有 Frontmatter 失败，将覆盖: {e}")

    # 合并：系统字段优先，用户已有字段保留
    merged = {**existing_meta, **frontmatter_data}

    # 构建新文件
    post = frontmatter.Post(content, **merged)
    output_path.write_text(
        frontmatter.dumps(post),
        encoding="utf-8",
    )
    logger.info(f"[Writer] 已写入: {output_path}")


def build_frontmatter(
    source_file: str,
    source_path: str,
    source_hash: str,
    converter: str,
    extra: Optional[dict] = None,
) -> dict:
    """
    构建标准 Frontmatter 字典。

    Args:
        source_file:  源文件名（不含路径）
        source_path:  源文件完整路径
        source_hash:  SHA256 哈希字符串
        converter:    使用的转换器名称
        extra:        额外字段（如 AI 生成的 tags、summary）
    """
    now = datetime.now(tz=timezone.utc).isoformat()
    meta = {
        "source_file": source_file,
        "source_path": source_path,
        "source_hash": source_hash,
        "converter": converter,
        "converted_at": now,
        "last_sync": now,
    }
    if extra:
        meta.update(extra)
    return meta


def mark_source_deleted(output_path: Path) -> None:
    """在 Frontmatter 中标记源文件已删除。"""
    if not output_path.exists():
        return
    try:
        post = frontmatter.load(str(output_path))
        post.metadata["source_deleted"] = True
        post.metadata["source_deleted_at"] = datetime.now(tz=timezone.utc).isoformat()
        output_path.write_text(frontmatter.dumps(post), encoding="utf-8")
        logger.info(f"[Writer] 已标记 source_deleted: {output_path}")
    except Exception as e:
        logger.error(f"[Writer] 标记 source_deleted 失败: {e}")


def resolve_output_path(
    source_path: Path,
    vault_root: Path,
    import_root: str,
    output_dirs: dict[str, str],
    ext_override: Optional[str] = None,
    inbox_path_rules: Optional[list[dict]] = None,
    inbox_root: Optional[Path] = None,
) -> Optional[Path]:
    """
    根据源文件路径和 inbox_path_rules 计算输出 Markdown 路径。

    路由逻辑：
    1. 将源文件路径与 inbox_path_rules 逐条匹配
    2. 匹配到规则时，使用规则的 import_root 替代默认值
    3. 保留源文件在 inbox 内的相对子路径结构
    4. 输出格式：vault_root / matched_import_root / relative_subdir / stem.md

    示例（有路由规则）：
        source = D:/DocInbox/ue/T60-G1/空调/hvac.pdf
        rule match = 'ue' → import_root = '3G125/UE'
        → vault/3G125/UE/T60-G1/空调/hvac.md

    示例（无规则，默认）：
        source = D:/DocInbox/reports/annual.pdf
        → vault/Imported/PDF/annual.md
    """
    ext = (ext_override or source_path.suffix).lower().lstrip(".")
    sub_dir = output_dirs.get(ext, ext.upper())

    # 尝试匹配 inbox_path_rules
    if inbox_path_rules and inbox_root:
        try:
            rel = source_path.relative_to(inbox_root)  # 相对 inbox 的路径
            rel_parts = rel.parts  # ('ue', 'T60-G1', '空调', 'hvac.pdf')
            for rule in inbox_path_rules:
                match_key = rule.get("match", "").lower()
                # 匹配 inbox 下的第一级子目录名
                if rel_parts and rel_parts[0].lower() == match_key:
                    # 检查是否有 include_keywords 白名单
                    includes = rule.get("include_keywords")
                    if includes:
                        # 检查源文件路径中是否包含白名单关键字
                        source_str = str(source_path)
                        if not any(k in source_str for k in includes):
                            return None  # 不满足白名单，直接丢弃

                    rule_import_root = rule.get("import_root", import_root)
                    # 保留 match 目录之后的子路径结构（不含文件名）
                    sub_rel = Path(*rel_parts[1:-1]) if len(rel_parts) > 2 else Path()
                    stem = source_path.stem
                    return vault_root / rule_import_root / sub_rel / f"{stem}.md"
        except ValueError:
            pass  # source_path 不在 inbox_root 下，走默认逻辑

    # 默认：vault/import_root/格式子目录/filename.md
    stem = source_path.stem
    return vault_root / import_root / sub_dir / f"{stem}.md"

