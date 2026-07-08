"""
sync_daemon.py — Obsidian 文档自动同步守护进程

用法：
  python sync_daemon.py start               # 启动守护进程
  python sync_daemon.py start --config /path/to/config.yaml
  python sync_daemon.py status              # 查看同步状态
  python sync_daemon.py retry               # 手动触发失败重试
  python sync_daemon.py scan                # 扫描 Inbox 全量同步
  python sync_daemon.py detect-vaults       # 自动检测 Obsidian Vault
"""

import json
import signal
import sys
import time
from pathlib import Path
from queue import Queue

import click
import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger
from rich.console import Console
from rich.table import Table

from ai.post_processor import AIPostProcessor
from converters.registry import registry as conv_registry
from core.scheduler import ConversionScheduler
from core.state_db import StateDB
from core.watcher import InboxWatcher


import io
import os

# Windows GBK 终端 UTF-8 强制输出
if os.name == "nt":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

console = Console(file=sys.stdout, highlight=False)

# ------------------------------------------------------------------
# 配置加载
# ------------------------------------------------------------------

DEFAULT_CONFIG = Path(__file__).parent / "config.yaml"


def load_config(config_path: Path) -> dict:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def setup_logging(config: dict) -> None:
    log_cfg = config.get("logging", {})
    level = log_cfg.get("level", "INFO")
    log_file = Path(config["paths"].get("log_file", "logs/sync.log"))
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger.remove()
    if log_cfg.get("console", True):
        # Windows 下强制 UTF-8 输出，避免 GBK 乱码
        logger.add(sys.stderr, level=level, colorize=False,
                   format="{time:HH:mm:ss} | {level:<7} | {message}")

    max_bytes = log_cfg.get("max_size_mb", 10) * 1024 * 1024
    backup = log_cfg.get("backup_count", 5)
    logger.add(
        str(log_file),
        level=level,
        rotation=max_bytes,
        retention=backup,
        encoding="utf-8",
    )


# ------------------------------------------------------------------
# Vault 自动检测
# ------------------------------------------------------------------

def detect_obsidian_vaults() -> list[dict]:
    """从系统 Obsidian 配置文件自动检测所有 Vault。"""
    import os
    candidates = [
        Path(os.environ.get("APPDATA", "")) / "obsidian" / "obsidian.json",
        Path.home() / ".config" / "obsidian" / "obsidian.json",
        Path.home() / "Library" / "Application Support" / "obsidian" / "obsidian.json",
    ]
    for cfg_path in candidates:
        if cfg_path.exists():
            with open(cfg_path, encoding="utf-8") as f:
                data = json.load(f)
            vaults = []
            for vault_id, vault_info in data.get("vaults", {}).items():
                vaults.append({
                    "id": vault_id,
                    "path": vault_info.get("path", ""),
                    "ts": vault_info.get("ts", 0),
                })
            return sorted(vaults, key=lambda v: -v["ts"])  # 最近使用的排前面
    return []


# ------------------------------------------------------------------
# CLI 入口
# ------------------------------------------------------------------

@click.group()
def cli():
    """Obsidian 文档自动同步守护进程"""
    pass


@cli.command()
@click.option("--config", "-c", default=str(DEFAULT_CONFIG), help="配置文件路径")
def start(config: str):
    """启动文件监听守护进程（持续运行）"""
    cfg_path = Path(config)
    if not cfg_path.exists():
        console.print(f"[red]✗ 配置文件不存在: {cfg_path}[/red]")
        console.print("  请先复制 config.yaml 并按需修改路径配置")
        sys.exit(1)

    cfg = load_config(cfg_path)
    setup_logging(cfg)

    # 初始化各组件
    paths = cfg["paths"]
    state_db = StateDB(Path(paths["state_db"]))
    ai_proc = AIPostProcessor(cfg.get("ai", {}))

    conv_registry.auto_discover(cfg)

    event_queue: Queue = Queue()
    scheduler = ConversionScheduler(
        event_queue=event_queue,
        state_db=state_db,
        registry=conv_registry,
        ai_processor=ai_proc,
        config=cfg,
    )

    inbox_path = Path(paths["inbox"])
    watcher_cfg = cfg.get("watcher", {})
    excluded_exts: set[str] = set(watcher_cfg.get("exclude_extensions", []))
    watcher = InboxWatcher(
        inbox_path=inbox_path,
        out_queue=event_queue,
        supported_exts=conv_registry.supported_extensions(),
        recursive=watcher_cfg.get("recursive", True),
        debounce_seconds=watcher_cfg.get("debounce_seconds", 2.0),
        settle_seconds=watcher_cfg.get("settle_seconds", 1.0),
        excluded_exts=excluded_exts,
    )

    # 定时重试任务
    retry_interval = cfg.get("error_handling", {}).get("retry_interval_seconds", 300)
    job_scheduler = BackgroundScheduler()
    job_scheduler.add_job(
        scheduler.retry_failed,
        "interval",
        seconds=retry_interval,
        id="auto_retry",
    )

    # 启动
    watcher.start()
    scheduler.start()
    job_scheduler.start()

    # 启动时全量扫描（处理 daemon 停机期间的变化）
    logger.info("[Main] 启动时执行全量扫描...")
    _scan_inbox(inbox_path, event_queue, conv_registry.supported_extensions(), excluded_exts)

    console.print(f"\n[bold green][OK] 守护进程已启动[/bold green]")
    console.print(f"  [*] 监听目录: {inbox_path}")
    console.print(f"  [*] Vault:    {paths['vault']}")
    console.print(f"  [*] AI 后处理: {'启用 (' + cfg.get('ai',{}).get('provider','') + ')' if ai_proc.is_enabled() else '禁用'}")
    console.print(f"\n  按 Ctrl+C 停止\n")

    # 优雅退出
    def _shutdown(sig, frame):
        logger.info("[Main] 收到停止信号，正在退出...")
        watcher.stop()
        scheduler.stop()
        job_scheduler.shutdown(wait=False)
        console.print("\n[yellow]守护进程已停止[/yellow]")
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    while True:
        time.sleep(1)


@cli.command()
@click.option("--config", "-c", default=str(DEFAULT_CONFIG))
def scan(config: str):
    """全量扫描 Inbox 目录，处理所有文件（包括历史未处理文件）"""
    cfg = load_config(Path(config))
    setup_logging(cfg)

    paths = cfg["paths"]
    state_db = StateDB(Path(paths["state_db"]))
    ai_proc = AIPostProcessor(cfg.get("ai", {}))
    conv_registry.auto_discover(cfg)

    event_queue: Queue = Queue()
    scheduler = ConversionScheduler(
        event_queue=event_queue,
        state_db=state_db,
        registry=conv_registry,
        ai_processor=ai_proc,
        config=cfg,
    )
    scheduler.start()

    inbox_path = Path(paths["inbox"])
    count = _scan_inbox(inbox_path, event_queue, conv_registry.supported_extensions())
    console.print(f"[green]已加入队列: {count} 个文件[/green]")

    # 等待队列处理完
    event_queue.join()
    scheduler.stop()
    console.print("[bold green]✓ 全量扫描完成[/bold green]")


@cli.command()
@click.option("--config", "-c", default=str(DEFAULT_CONFIG))
def retry(config: str):
    """手动触发失败文件重试"""
    cfg = load_config(Path(config))
    setup_logging(cfg)
    paths = cfg["paths"]
    state_db = StateDB(Path(paths["state_db"]))
    ai_proc = AIPostProcessor(cfg.get("ai", {}))
    conv_registry.auto_discover(cfg)

    event_queue: Queue = Queue()
    scheduler = ConversionScheduler(
        event_queue=event_queue,
        state_db=state_db,
        registry=conv_registry,
        ai_processor=ai_proc,
        config=cfg,
    )
    scheduler.start()
    count = scheduler.retry_failed()
    event_queue.join()
    scheduler.stop()
    console.print(f"[green]已重试: {count} 个失败文件[/green]")


@cli.command()
@click.option("--config", "-c", default=str(DEFAULT_CONFIG))
def status(config: str):
    """查看同步状态统计"""
    cfg = load_config(Path(config))
    state_db = StateDB(Path(cfg["paths"]["state_db"]))
    stats = state_db.stats()

    table = Table(title="[bold]同步状态统计[/bold]", show_header=True)
    table.add_column("状态", style="cyan")
    table.add_column("数量", justify="right", style="bold")
    for s, cnt in stats.items():
        color = {"ok": "green", "failed": "red", "pending": "yellow"}.get(s, "white")
        table.add_row(s, f"[{color}]{cnt}[/{color}]")
    try:
        console.print(table)
    except UnicodeEncodeError:
        for s, cnt in stats.items():
            print(f"  {s}: {cnt}")


@cli.command("detect-vaults")
def detect_vaults():
    """自动检测本机 Obsidian Vault 路径"""
    vaults = detect_obsidian_vaults()
    if not vaults:
        console.print("[yellow]未检测到 Obsidian Vault，请手动配置 config.yaml[/yellow]")
        return
    console.print("[bold]检测到以下 Obsidian Vault：[/bold]")
    for i, v in enumerate(vaults, 1):
        try:
            console.print(f"  {i}. [cyan]{v['path']}[/cyan]  (id: {v['id'][:8]}...)")
        except UnicodeEncodeError:
            print(f"  {i}. {v['path']}  (id: {v['id'][:8]}...)")
    print(f"\n将你想用的 vault 路径填入 config.yaml 的 paths.vault 字段")


# ------------------------------------------------------------------
# 内部工具
# ------------------------------------------------------------------

def _scan_inbox(inbox: Path, queue: Queue, supported_exts: set, excluded_exts: set | None = None) -> int:
    """递归扫描 Inbox 目录，把所有支持格式的文件加入事件队列。"""
    from core.watcher import FileEvent
    excluded = excluded_exts or set()
    count = 0
    for f in inbox.rglob("*"):
        if f.is_file():
            ext = f.suffix.lower().lstrip(".")
            if ext in supported_exts and ext not in excluded:
                queue.put(FileEvent("created", str(f)))
                count += 1
    return count


if __name__ == "__main__":
    cli()
