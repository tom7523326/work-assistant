#!/usr/bin/env python3
"""
数据备份 + 并发保护工具
═══════════════════════
所有 App 和 AI 对核心 JSON 的写操作都应通过这里。

核心 API:
    safe_load(path) -> dict          安全读
    safe_save(path, data)             安全写（自动备份 + 文件锁）
    atomic_update(path, mutator)      原子读-改-写（防并发覆盖）

备份策略:
    每次写之前自动备份到 数据/.history/<basename>_YYYYMMDD_HHMMSS.json
    保留最近 30 份，自动清理更早的
"""

import json
import os
import shutil
import time
import fcntl
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
HISTORY_DIR = BASE_DIR / "数据" / ".history"
MAX_HISTORY = 30
LOCK_TIMEOUT = 5.0  # 秒


def _ensure_history_dir():
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def _backup(path: Path):
    """写之前先备份当前文件"""
    if not path.exists():
        return
    _ensure_history_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{path.stem}_{ts}.json"
    backup_path = HISTORY_DIR / backup_name
    try:
        shutil.copy2(path, backup_path)
    except Exception:
        pass
    _cleanup_old_backups(path.stem)


def _cleanup_old_backups(stem: str):
    """保留最近 MAX_HISTORY 份备份"""
    if not HISTORY_DIR.exists():
        return
    files = sorted(
        [f for f in HISTORY_DIR.glob(f"{stem}_*.json")],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    for f in files[MAX_HISTORY:]:
        try:
            f.unlink()
        except Exception:
            pass


class FileLock:
    """文件锁上下文管理器（fcntl 实现，跨进程）"""

    def __init__(self, target: Path, timeout: float = LOCK_TIMEOUT):
        self.lock_path = target.parent / f".{target.name}.lock"
        self.timeout = timeout
        self.fp = None

    def __enter__(self):
        self.fp = open(self.lock_path, "w")
        start = time.time()
        while True:
            try:
                fcntl.flock(self.fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except (BlockingIOError, OSError):
                if time.time() - start > self.timeout:
                    raise TimeoutError(f"无法获取文件锁: {self.lock_path}")
                time.sleep(0.05)

    def __exit__(self, *args):
        try:
            fcntl.flock(self.fp.fileno(), fcntl.LOCK_UN)
            self.fp.close()
        except Exception:
            pass


def safe_load(path) -> dict:
    """安全读：加共享锁"""
    path = Path(path)
    with FileLock(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)


def safe_save(path, data: dict):
    """安全写：备份 + 加排他锁 + 原子替换"""
    path = Path(path)
    with FileLock(path):
        _backup(path)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)


def atomic_update(path, mutator):
    """原子读-改-写
    
    mutator(data) -> data  函数会拿到当前数据，返回修改后的数据
    
    用法:
        def add_task(data):
            data["待办"].append({...})
            return data
        atomic_update("数据/12_待办.json", add_task)
    """
    path = Path(path)
    with FileLock(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        new_data = mutator(data)
        _backup(path)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        return new_data


def list_history(stem: str = None):
    """列出历史备份"""
    if not HISTORY_DIR.exists():
        return []
    pattern = f"{stem}_*.json" if stem else "*.json"
    files = sorted(HISTORY_DIR.glob(pattern), key=lambda f: f.stat().st_mtime, reverse=True)
    return [
        {
            "name": f.name,
            "mtime": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "size_kb": round(f.stat().st_size / 1024, 1),
        }
        for f in files
    ]


def restore_from(backup_name: str, target: Path):
    """从备份恢复"""
    backup_path = HISTORY_DIR / backup_name
    if not backup_path.exists():
        raise FileNotFoundError(backup_name)
    target = Path(target)
    with FileLock(target):
        _backup(target)  # 当前文件也备份
        shutil.copy2(backup_path, target)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        for h in list_history():
            print(f"  {h['mtime']}  {h['size_kb']:>6} KB  {h['name']}")
    else:
        print("数据备份工具")
        print("  python3 数据备份.py list   # 列出历史备份")
        print(f"  历史目录: {HISTORY_DIR}")
