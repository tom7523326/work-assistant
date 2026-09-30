#!/usr/bin/env python3
"""
菜单栏常驻图标
═══════════════
在 macOS 顶部状态栏显示一个小图标：
  · 显示今日聚焦数量
  · 点击展开菜单：今日任务列表、还款提醒、快捷操作

依赖：rumps (pip install rumps)
运行：/usr/bin/python3 菜单栏.py
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, date

try:
    import rumps
except ImportError:
    print("❌ 缺少 rumps，请运行: /usr/bin/python3 -m pip install --user rumps")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent
TODO_FILE = BASE_DIR / "数据" / "12_待办.json"
REPAY_FILE = BASE_DIR / "数据" / "14_还款日历.json"
APP_SCRIPT = BASE_DIR / "任务看板.py"

REFRESH_INTERVAL = 60  # 秒


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _dl_parse(s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        if " " in s:
            return datetime.strptime(s, "%Y-%m-%d %H:%M")
        return datetime.strptime(s, "%Y-%m-%d").replace(hour=23, minute=59)
    except Exception:
        return None


def find_python_with_tk():
    """找带 tkinter 的 Python"""
    candidates = [
        "/opt/homebrew/opt/python@3.12/libexec/bin/python3",
        "/opt/homebrew/opt/python@3.13/libexec/bin/python3",
        "/opt/homebrew/bin/python3",
        "/usr/local/bin/python3",
    ]
    for p in candidates:
        if Path(p).exists():
            r = subprocess.run([p, "-c", "import tkinter"], capture_output=True)
            if r.returncode == 0:
                return p
    return None


class TaskBoardMenuBar(rumps.App):
    def __init__(self):
        super().__init__("📋", quit_button=None)
        self._python = find_python_with_tk()
        self._build_menu()
        # 每 60 秒刷新
        self._timer = rumps.Timer(self._refresh, REFRESH_INTERVAL)
        self._timer.start()
        self._refresh(None)

    def _build_menu(self):
        # 标题区由动态菜单填充
        pass

    def _refresh(self, _):
        """每分钟刷新菜单"""
        data = load_json(TODO_FILE)
        repay = load_json(REPAY_FILE) or {"还款": []}

        if not data:
            self.title = "📋 ?"
            return

        active = [t for t in data.get("待办", [])
                  if t.get("status") in ("todo", "doing", "blocked")]
        focus_ids = data.get("_today_focus", [])
        focus = [t for t in active if t.get("id") in focus_ids]

        today = date.today()
        overdue = sum(1 for t in active
                      if (dl := _dl_parse(t.get("deadline", ""))) and dl.date() < today)

        # 状态栏图标 + 数字
        if overdue > 0:
            self.title = f"⚠ {len(focus)}"
        elif len(focus) > 0:
            self.title = f"📋 {len(focus)}"
        else:
            self.title = "📋 ✓"

        # 重建菜单
        self.menu.clear()

        # 标题行
        info_str = f"今日聚焦 {len(focus)} 项"
        if overdue:
            info_str += f"  ·  ⚠ {overdue} 项逾期"
        self.menu.add(rumps.MenuItem(info_str, callback=None))
        self.menu.add(rumps.separator)

        # 还款提醒（未来 3 天）
        upcoming_repay = []
        for r in repay.get("还款", []):
            if r.get("status") == "paid":
                continue
            d = _dl_parse(r.get("due_date", ""))
            if d:
                days = (d.date() - today).days
                if -1 <= days <= 3:
                    upcoming_repay.append((days, r))

        if upcoming_repay:
            self.menu.add(rumps.MenuItem("💰 近期还款", callback=None))
            upcoming_repay.sort(key=lambda x: x[0])
            for days, r in upcoming_repay[:5]:
                if days < 0:
                    day_label = f"逾期 {-days} 天"
                elif days == 0:
                    day_label = "今天"
                elif days == 1:
                    day_label = "明天"
                else:
                    day_label = f"{days} 天后"
                title = f"   {r.get('title', '')}  ¥{r.get('amount', 0):,.0f}  ({day_label})"
                self.menu.add(rumps.MenuItem(title, callback=None))
            self.menu.add(rumps.separator)

        # 今日聚焦列表
        if focus:
            self.menu.add(rumps.MenuItem("★ 今日聚焦", callback=None))
            for t in focus[:10]:
                title = t.get("title", "")[:50]
                if len(title) >= 50:
                    title += "..."
                pri = t.get("priority", "")
                title_with_pri = f"   {pri}  {title}"
                # 点击 = 标记完成
                item = rumps.MenuItem(
                    title_with_pri,
                    callback=lambda sender, task=t: self._mark_done(task)
                )
                self.menu.add(item)
            self.menu.add(rumps.separator)

        # 操作菜单
        self.menu.add(rumps.MenuItem("打开任务看板", callback=self._open_app))
        self.menu.add(rumps.MenuItem("新建任务...", callback=self._quick_add))
        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("刷新", callback=self._refresh))
        self.menu.add(rumps.MenuItem("退出", callback=self._quit))

    def _open_app(self, _):
        if not self._python or not APP_SCRIPT.exists():
            rumps.notification("任务看板", "启动失败", "找不到 App 或 Python")
            return
        subprocess.Popen([self._python, str(APP_SCRIPT)])

    def _quick_add(self, _):
        response = rumps.Window(
            message="输入任务标题（自动 P1 本周）",
            title="新建任务",
            default_text="",
            ok="添加",
            cancel="取消",
            dimensions=(320, 22),
        ).run()
        if not response.clicked or not response.text.strip():
            return
        title = response.text.strip()
        try:
            with open(TODO_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 生成 ID
            max_n = 0
            for t in data.get("待办", []):
                tid = t.get("id", "")
                if tid.startswith("T") and tid[1:].isdigit():
                    max_n = max(max_n, int(tid[1:]))
            new_id = f"T{max_n + 1:03d}"

            today = datetime.now().strftime("%Y-%m-%d")
            new_task = {
                "id": new_id,
                "title": title,
                "domain": "work",
                "type": "task",
                "priority": "P1",
                "status": "todo",
                "created": today,
                "deadline": "",
                "next_action_5min": "",
                "notes": "",
                "tags": ["菜单栏新增"],
            }
            data["待办"].append(new_task)
            data.setdefault("_today_focus", []).append(new_id)
            data["_today_focus_date"] = today
            data["_最后更新"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            with open(TODO_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._refresh(None)
            rumps.notification("已添加", title, "已加入今日聚焦")
        except Exception as e:
            rumps.notification("出错", str(e), "")

    def _mark_done(self, task):
        tid = task.get("id", "")
        title = task.get("title", "")
        response = rumps.alert(
            title="标记完成",
            message=title,
            ok="完成",
            cancel="取消",
        )
        if response != 1:
            return
        try:
            with open(TODO_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            today = datetime.now().strftime("%Y-%m-%d")
            for t in data["待办"]:
                if t.get("id") == tid:
                    t["status"] = "done"
                    t["_completed_at"] = today
                    t["_完成备注"] = "菜单栏标记完成"
                    for s in t.get("sub_tasks", []):
                        s["done"] = True
                    break
            if tid in data.get("_today_focus", []):
                data["_today_focus"].remove(tid)
            data["_最后更新"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            with open(TODO_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # 写事件流
            try:
                event_file = BASE_DIR / "数据" / "_事件流.jsonl"
                with open(event_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "event": "task_done",
                        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "actor": "MenuBar",
                        "task_id": tid,
                        "detail": title,
                    }, ensure_ascii=False) + "\n")
            except Exception:
                pass

            self._refresh(None)
        except Exception as e:
            rumps.notification("出错", str(e), "")

    def _quit(self, _):
        rumps.quit_application()


if __name__ == "__main__":
    TaskBoardMenuBar().run()
