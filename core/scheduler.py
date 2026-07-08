"""
core/scheduler.py — 事件调度与转换执行引擎

从 watcher 队列消费事件，执行转换、写入、AI 后处理，
并更新 SQLite 状态数据库。
"""

import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from queue import Empty, Queue
from typing import Optional

from loguru import logger

from ai.post_processor import AIPostProcessor
from converters.base import ConvertResult
from converters.registry import ConverterRegistry
from core.hasher import compute_file_hash, hash_changed
from core.output_writer import (
    build_frontmatter,
    mark_source_deleted,
    resolve_output_path,
    write_markdown,
)
from core.state_db import StateDB, SyncRecord
from core.watcher import FileEvent


class ConversionScheduler:
    """
    消费 FileEvent 队列，执行完整的转换流程：
      文件事件 → Hash 检查 → 转换 → AI后处理 → 写入 → 更新DB
    """

    def __init__(
        self,
        event_queue: Queue,
        state_db: StateDB,
        registry: ConverterRegistry,
        ai_processor: AIPostProcessor,
        config: dict,
    ) -> None:
        self._queue = event_queue
        self._db = state_db
        self._registry = registry
        self._ai = ai_processor
        self._cfg = config

        # 路径配置
        paths = config["paths"]
        self._vault = Path(paths["vault"])
        self._import_root = paths.get("import_root", "Imported")
        self._output_dirs: dict[str, str] = config.get("output_dirs", {})
        self._inbox_path_rules: list[dict] = config.get("inbox_path_rules", [])
        self._inbox_root = Path(paths["inbox"])
        self._failed_dir = self._vault / paths.get("failed_dir", "_Failed")
        self._trash_dir = self._vault / paths.get("trash_dir", "_Trash")
        self._delete_strategy = config.get("on_delete", {}).get("strategy", "mark_deleted")
        self._max_retries = config.get("error_handling", {}).get("max_retries", 3)
        self._move_failed_source = (
            config.get("error_handling", {}).get("move_failed_source", False)
        )

        self._running = False
        self._worker_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def start(self) -> None:
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._loop, daemon=True, name="scheduler-worker"
        )
        self._worker_thread.start()
        logger.info("[Scheduler] 调度器已启动")

    def stop(self) -> None:
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        logger.info("[Scheduler] 调度器已停止")

    # ------------------------------------------------------------------
    # 主循环
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        while self._running:
            try:
                event: FileEvent = self._queue.get(timeout=1.0)
                self._dispatch(event)
                self._queue.task_done()
            except Empty:
                continue
            except Exception as e:
                logger.error(f"[Scheduler] 未捕获异常: {e}", exc_info=True)

    def _dispatch(self, event: FileEvent) -> None:
        logger.debug(f"[Scheduler] 处理事件: {event}")
        if event.kind in ("created", "modified"):
            self._handle_upsert(Path(event.src_path))
        elif event.kind == "deleted":
            self._handle_delete(event.src_path)
        elif event.kind == "renamed":
            self._handle_rename(event.src_path, event.dest_path)

    # ------------------------------------------------------------------
    # 事件处理器
    # ------------------------------------------------------------------

    def _handle_upsert(self, source_path: Path) -> None:
        """新增或修改文件的处理流程。"""
        if not source_path.exists():
            logger.warning(f"[Scheduler] 文件不存在，跳过: {source_path}")
            return

        # Hash 变更检测
        record = self._db.get(str(source_path))
        stored_hash = record.source_hash if record else None
        if not hash_changed(source_path, stored_hash):
            logger.info(f"[Scheduler] 内容未变化，跳过: {source_path.name}")
            return

        # 查找转换器
        ext = source_path.suffix.lower().lstrip(".")
        converter = self._registry.get(ext)
        if converter is None:
            logger.warning(f"[Scheduler] 无支持的转换器: {source_path.name} (.{ext})")
            return

        # 计算输出路径
        output_path = resolve_output_path(
            source_path=source_path,
            vault_root=self._vault,
            import_root=self._import_root,
            output_dirs=self._output_dirs,
            inbox_path_rules=self._inbox_path_rules,
            inbox_root=self._inbox_root,
        )
        if output_path is None:
            logger.debug(f"[Scheduler] 被路由规则过滤，跳过: {source_path.name}")
            return

        converter_config = self._cfg.get("converters", {}).get(ext, {})

        # 执行转换
        logger.info(f"[Scheduler] 开始转换: {source_path.name} → {output_path}")
        result: ConvertResult = converter.convert(
            source_path=source_path,
            output_dir=output_path.parent,
            config=converter_config,
        )

        if not result.success:
            self._handle_failure(source_path, record, result.error or "未知错误")
            return

        # 计算新 Hash
        new_hash = compute_file_hash(source_path)

        # AI 后处理
        ai_extra = self._ai.process(result.markdown, {})

        # 写入 Markdown
        fm = build_frontmatter(
            source_file=source_path.name,
            source_path=str(source_path),
            source_hash=new_hash,
            converter=result.converter_name,
            extra=ai_extra,
        )
        write_markdown(
            content=result.markdown,
            output_path=output_path,
            frontmatter_data=fm,
            overwrite=True,
        )

        # 更新 DB
        now = datetime.now(tz=timezone.utc).isoformat()
        self._db.upsert(
            SyncRecord(
                source_path=str(source_path),
                source_hash=new_hash,
                output_path=str(output_path),
                converter=result.converter_name,
                status="ok",
                converted_at=now,
                last_sync=now,
                retry_count=0,
            )
        )
        logger.info(f"[Scheduler] ✓ 完成: {source_path.name}")

    def _handle_delete(self, source_path_str: str) -> None:
        """源文件删除的处理流程。"""
        record = self._db.get(source_path_str)
        if not record or not record.output_path:
            logger.info(f"[Scheduler] 删除事件：无对应 MD 记录，忽略: {source_path_str}")
            return

        output_path = Path(record.output_path)
        strategy = self._delete_strategy

        if strategy == "mark_deleted":
            mark_source_deleted(output_path)
            self._db.mark_status(source_path_str, "source_deleted")
            logger.info(f"[Scheduler] 已标记 source_deleted: {output_path.name}")

        elif strategy == "move_to_trash":
            if output_path.exists():
                self._trash_dir.mkdir(parents=True, exist_ok=True)
                dest = self._trash_dir / output_path.name
                shutil.move(str(output_path), str(dest))
                self._db.mark_status(source_path_str, "source_deleted")
                logger.info(f"[Scheduler] 已移至回收: {dest}")

        elif strategy == "delete":
            if output_path.exists():
                output_path.unlink()
                self._db.mark_status(source_path_str, "source_deleted")
                logger.info(f"[Scheduler] 已删除 MD: {output_path.name}")

        else:
            logger.info(f"[Scheduler] 删除策略=ignore，跳过")

    def _handle_rename(self, old_path_str: str, new_path_str: str) -> None:
        """源文件重命名的处理流程。"""
        record = self._db.get(old_path_str)
        new_source = Path(new_path_str)

        if record and record.output_path:
            old_output = Path(record.output_path)
            new_output = resolve_output_path(
                source_path=new_source,
                vault_root=self._vault,
                import_root=self._import_root,
                output_dirs=self._output_dirs,
                inbox_path_rules=self._inbox_path_rules,
                inbox_root=self._inbox_root,
            )
            if new_output is None:
                # 移动后被过滤规则命中，当作删除处理
                if old_output.exists():
                    old_output.unlink()
                return

            # 重命名输出文件
            if old_output.exists():
                new_output.parent.mkdir(parents=True, exist_ok=True)
                old_output.rename(new_output)
                logger.info(
                    f"[Scheduler] 重命名 MD: {old_output.name} → {new_output.name}"
                )
            # 更新 DB
            self._db.rename(old_path_str, new_path_str)

        # 重新转换新文件（内容可能不变，Hash 检测会自动跳过）
        self._handle_upsert(new_source)

    # ------------------------------------------------------------------
    # 错误处理
    # ------------------------------------------------------------------

    def _handle_failure(
        self, source_path: Path, record: Optional[SyncRecord], error: str
    ) -> None:
        retry_count = record.retry_count if record else 0
        logger.error(
            f"[Scheduler] ✗ 转换失败 (retry={retry_count}): "
            f"{source_path.name} — {error}"
        )
        new_count = self._db.increment_retry(str(source_path))
        self._db.mark_status(str(source_path), "failed", error_msg=error)

        if self._move_failed_source and retry_count >= self._max_retries:
            self._failed_dir.mkdir(parents=True, exist_ok=True)
            dest = self._failed_dir / source_path.name
            try:
                shutil.copy2(str(source_path), str(dest))
                logger.info(f"[Scheduler] 已复制失败文件到: {dest}")
            except Exception as e:
                logger.warning(f"[Scheduler] 复制失败文件时出错: {e}")

    # ------------------------------------------------------------------
    # 手动重试（外部调用）
    # ------------------------------------------------------------------

    def retry_failed(self) -> int:
        """触发所有失败记录的重试，返回重试数量。"""
        records = self._db.list_pending_retry(self._max_retries)
        count = 0
        for rec in records:
            p = Path(rec.source_path)
            if p.exists():
                logger.info(f"[Scheduler] 重试: {p.name}")
                self._handle_upsert(p)
                count += 1
        return count
