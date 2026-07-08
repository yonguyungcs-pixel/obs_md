"""
core/watcher.py — 文件系统监听

基于 watchdog 监听 Inbox 目录的文件变化，防抖后送入事件队列。
"""

import threading
import time
from pathlib import Path
from queue import Queue
from typing import Callable, Set

from watchdog.events import (
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileSystemEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

from loguru import logger


# ------------------------------------------------------------------
# 事件数据结构
# ------------------------------------------------------------------

class FileEvent:
    """标准化的文件事件，屏蔽 watchdog 内部细节。"""

    __slots__ = ("kind", "src_path", "dest_path")

    def __init__(self, kind: str, src_path: str, dest_path: str = "") -> None:
        self.kind = kind          # created | modified | deleted | renamed
        self.src_path = src_path
        self.dest_path = dest_path  # 仅 renamed 时有效

    def __repr__(self) -> str:
        if self.dest_path:
            return f"FileEvent({self.kind}: {self.src_path!r} → {self.dest_path!r})"
        return f"FileEvent({self.kind}: {self.src_path!r})"


# ------------------------------------------------------------------
# 防抖 Handler
# ------------------------------------------------------------------

class _DebouncedHandler(FileSystemEventHandler):
    """
    将 watchdog 原始事件防抖后送入输出队列。
    同一文件在 debounce_seconds 内的多次事件会被合并成最后一次事件。
    """

    def __init__(
        self,
        out_queue: Queue,
        supported_exts: Set[str],
        debounce_seconds: float,
        settle_seconds: float,
        excluded_exts: Set[str] | None = None,
    ) -> None:
        super().__init__()
        self._queue = out_queue
        self._supported_exts = supported_exts
        self._excluded_exts: Set[str] = excluded_exts or set()
        self._debounce = debounce_seconds
        self._settle = settle_seconds
        self._pending: dict[str, tuple[float, FileEvent]] = {}  # path → (fire_at, event)
        self._lock = threading.Lock()

        # 后台线程：定期检查防抖到期事件
        self._timer_thread = threading.Thread(
            target=self._flush_loop, daemon=True, name="debounce-flusher"
        )
        self._timer_thread.start()

    # ---- watchdog 回调 ----

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._schedule(event.src_path, FileEvent("created", event.src_path))

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._schedule(event.src_path, FileEvent("modified", event.src_path))

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._schedule(event.src_path, FileEvent("deleted", event.src_path))

    def on_moved(self, event: FileMovedEvent) -> None:
        if not event.is_directory:
            fe = FileEvent("renamed", event.src_path, event.dest_path)
            # 以目标路径作为防抖 key，避免 src 和 dest 都触发
            self._schedule(event.dest_path, fe)

    # ---- 内部 ----

    def _is_supported(self, path: str) -> bool:
        ext = Path(path).suffix.lower().lstrip(".")
        if ext in self._excluded_exts:
            return False
        return ext in self._supported_exts

    def _schedule(self, key: str, event: FileEvent) -> None:
        if not self._is_supported(key) and not self._is_supported(event.src_path):
            return
        fire_at = time.monotonic() + self._debounce
        with self._lock:
            self._pending[key] = (fire_at, event)
        logger.debug(f"[Watcher] 调度防抖事件: {event}")

    def _flush_loop(self) -> None:
        while True:
            time.sleep(0.2)
            now = time.monotonic()
            to_fire: list[FileEvent] = []
            with self._lock:
                expired_keys = [k for k, (t, _) in self._pending.items() if t <= now]
                for k in expired_keys:
                    _, event = self._pending.pop(k)
                    to_fire.append(event)
            for event in to_fire:
                # 额外等待文件稳定（避免文件还在写入中）
                if event.kind in ("created", "modified"):
                    time.sleep(self._settle)
                logger.info(f"[Watcher] → 队列: {event}")
                self._queue.put(event)


# ------------------------------------------------------------------
# 主 Watcher 类
# ------------------------------------------------------------------

class InboxWatcher:
    """监听 Inbox 目录并将文件事件推入队列。"""

    def __init__(
        self,
        inbox_path: Path,
        out_queue: Queue,
        supported_exts: Set[str],
        recursive: bool = True,
        debounce_seconds: float = 2.0,
        settle_seconds: float = 1.0,
        excluded_exts: Set[str] | None = None,
    ) -> None:
        self._path = inbox_path
        self._recursive = recursive
        self._observer = Observer()
        handler = _DebouncedHandler(
            out_queue=out_queue,
            supported_exts=supported_exts,
            debounce_seconds=debounce_seconds,
            settle_seconds=settle_seconds,
            excluded_exts=excluded_exts,
        )
        self._observer.schedule(handler, str(inbox_path), recursive=recursive)

    def start(self) -> None:
        self._path.mkdir(parents=True, exist_ok=True)
        self._observer.start()
        logger.info(f"[Watcher] 开始监听: {self._path} (recursive={self._recursive})")

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join()
        logger.info("[Watcher] 已停止")
