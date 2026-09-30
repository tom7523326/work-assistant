#!/usr/bin/env python3
"""
工作助手 · 任务看板 v4
─────────────────────
设计：Things 3（Today 抽象） + Linear（信息密度） + Apple HIG
功能：
  - Today / 全部 / 已完成 三视图
  - 任务推迟（明天/后天/下周/选日期）
  - 子任务展开 + 勾选
  - 习惯打卡（streak）
  - 还款日历 banner
  - 事件流（写入 _事件流.jsonl，AI 可读）
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta, date

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, simpledialog
except ImportError:
    print("❌ 缺少 tkinter，请运行: brew install python-tk")
    sys.exit(1)

# 引入数据备份层
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from 数据备份 import safe_load, safe_save, atomic_update
    USE_SAFE_IO = True
except ImportError:
    USE_SAFE_IO = False

# ═══════════════════════════════════════
# 路径 & 常量
# ═══════════════════════════════════════
BASE_DIR = Path(__file__).resolve().parent
TODO_FILE = BASE_DIR / "数据" / "12_待办.json"
REPAY_FILE = BASE_DIR / "数据" / "14_还款日历.json"
EVENT_FILE = BASE_DIR / "数据" / "_事件流.jsonl"
CALENDAR_NAME = "工作助手"
POLL_MS = 3000

# 设计令牌
class C:
    BG          = "#FAFAFA"
    SURFACE     = "#FFFFFF"
    SURFACE_2   = "#F4F4F5"
    SURFACE_3   = "#EEEEF0"
    BORDER      = "#E4E4E7"
    BORDER_SOFT = "#F1F1F3"

    TEXT        = "#18181B"
    TEXT_2      = "#52525B"
    TEXT_3      = "#A1A1AA"
    TEXT_INV    = "#FAFAFA"

    BRAND       = "#000000"
    BRAND_HOVER = "#27272A"
    ACCENT      = "#3B82F6"
    SUCCESS     = "#10B981"
    WARNING     = "#F59E0B"
    DANGER      = "#EF4444"

    P0 = "#EF4444"
    P1 = "#F59E0B"
    P2 = "#3B82F6"
    P3 = "#71717A"

    BANNER_BG   = "#FEF3C7"  # 还款 banner 琥珀色
    BANNER_FG   = "#92400E"
    BANNER_BORDER = "#FCD34D"

PRIORITY_CFG = {
    "P0": {"label": "今天",      "color": C.P0},
    "P1": {"label": "本周",      "color": C.P1},
    "P2": {"label": "本月",      "color": C.P2},
    "P3": {"label": "有空再说",  "color": C.P3},
}
PRIORITY_ORDER = ["P0", "P1", "P2", "P3"]

DOMAIN_LABEL = {
    "family": "家庭", "work": "工作", "finance": "财务",
    "life": "生活", "growth": "成长",
}
WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

# 字体（优先 SF Pro，回退到系统）
FONT_FAMILY = "SF Pro Text"
FONT_DISPLAY = "SF Pro Display"


# ═══════════════════════════════════════
# 数据层（带备份 + 并发保护）
# ═══════════════════════════════════════
def load_todo() -> dict:
    if USE_SAFE_IO:
        return safe_load(TODO_FILE)
    with open(TODO_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_todo(data: dict):
    data["_最后更新"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    if USE_SAFE_IO:
        safe_save(TODO_FILE, data)
    else:
        with open(TODO_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def load_repay() -> dict:
    try:
        if USE_SAFE_IO:
            return safe_load(REPAY_FILE)
        with open(REPAY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"还款": []}

def next_id(data: dict) -> str:
    max_n = 0
    for t in data.get("待办", []):
        tid = t.get("id", "")
        if tid.startswith("T") and tid[1:].isdigit():
            max_n = max(max_n, int(tid[1:]))
    return f"T{max_n + 1:03d}"

def log_event(event: str, detail: str = "", task_id: str = ""):
    """写事件流，供 AI 读取"""
    try:
        line = {
            "event": event,
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "actor": "App",
            "task_id": task_id,
            "detail": detail,
        }
        with open(EVENT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ═══════════════════════════════════════
# 日历集成
# ═══════════════════════════════════════
def _osa(s: str):
    r = subprocess.run(["osascript", "-e", s], capture_output=True, text=True)
    return r.returncode == 0, r.stderr

def ensure_calendar() -> bool:
    ok, err = _osa(f'''
tell application "Calendar"
    if not (exists calendar "{CALENDAR_NAME}") then
        make new calendar with properties {{name:"{CALENDAR_NAME}"}}
    end if
end tell''')
    return ok or "not allowed" not in err.lower()

def add_event(task: dict) -> tuple:
    title = task.get("title", "").replace("\\", "\\\\").replace('"', '\\"')
    notes = task.get("next_action_5min", "")[:200].replace("\\", "\\\\").replace('"', '\\"')
    tid = task.get("id", "")
    dl = task.get("deadline", "")
    try:
        s = dl.strip()
        dt = datetime.strptime(s, "%Y-%m-%d %H:%M") if " " in s else \
             datetime.strptime(s, "%Y-%m-%d").replace(hour=9, minute=0)
    except Exception:
        dt = (datetime.now() + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    script = f'''
tell application "Calendar"
    tell calendar "{CALENDAR_NAME}"
        set d to current date
        set year of d to {dt.year}
        set month of d to {dt.month}
        set day of d to {dt.day}
        set hours of d to {dt.hour}
        set minutes of d to {dt.minute}
        set seconds of d to 0
        set endD to d + 60 * 60
        make new event with properties {{summary:"[{tid}] {title}", start date:d, end date:endD, description:"{notes}"}}
    end tell
    synchronize
end tell'''
    return _osa(script)


# ═══════════════════════════════════════
# UI 组件
# ═══════════════════════════════════════
class HoverLabel(tk.Label):
    """通用悬浮按钮（Label 实现，避免 macOS Button 丑陋样式）"""
    def __init__(self, parent, text, command=None,
                 bg=C.SURFACE, fg=C.TEXT_2,
                 hover_bg=C.SURFACE_2, hover_fg=C.TEXT,
                 font=None, **kwargs):
        super().__init__(parent, text=text, bg=bg, fg=fg, font=font,
                         cursor="hand2", **kwargs)
        self._bg, self._fg = bg, fg
        self._hbg, self._hfg = hover_bg, hover_fg
        self.bind("<Enter>", lambda e: self.config(bg=self._hbg, fg=self._hfg))
        self.bind("<Leave>", lambda e: self.config(bg=self._bg, fg=self._fg))
        if command:
            self.bind("<Button-1>", lambda e: command())


# ═══════════════════════════════════════
# 任务卡片
# ═══════════════════════════════════════
class TaskCard(tk.Frame):
    def __init__(self, parent, task, app, in_today=False, **kwargs):
        super().__init__(parent, bg=C.SURFACE, **kwargs)
        self.task = task
        self.app = app
        self.in_today = in_today
        self._expanded = False
        self._build()

    def _build(self):
        task = self.task
        # ─ 主卡片内容 ─
        self.wrap = tk.Frame(self, bg=C.SURFACE)
        self.wrap.pack(fill="x", padx=18, pady=12)

        # 右键菜单（卡片整体）
        self.bind("<Button-2>", lambda e: self._show_context_menu(e))
        self.bind("<Button-3>", lambda e: self._show_context_menu(e))
        self.wrap.bind("<Button-2>", lambda e: self._show_context_menu(e))
        self.wrap.bind("<Button-3>", lambda e: self._show_context_menu(e))

        # 第一行：复选框 + 标题 + 元数据
        row1 = tk.Frame(self.wrap, bg=C.SURFACE)
        row1.pack(fill="x")

        # 复选框
        self.check = tk.Label(row1, text="○", font=(FONT_DISPLAY, 16),
                              bg=C.SURFACE, fg=C.TEXT_3, cursor="hand2")
        self.check.pack(side="left", padx=(0, 10), anchor="n")
        self.check.bind("<Enter>", lambda e: self.check.config(fg=C.SUCCESS, text="◉"))
        self.check.bind("<Leave>", lambda e: self.check.config(fg=C.TEXT_3, text="○"))
        self.check.bind("<Button-1>", lambda e: self.app._mark_done(task))

        # 标题 + 类型标记
        title_frame = tk.Frame(row1, bg=C.SURFACE)
        title_frame.pack(side="left", fill="x", expand=True, anchor="n")

        title_text = task.get("title", "")
        ttype = task.get("type", "task")

        title_lbl = tk.Label(title_frame, text=title_text,
                             font=(FONT_FAMILY, 13),
                             bg=C.SURFACE, fg=C.TEXT,
                             anchor="w", justify="left",
                             wraplength=420, cursor="hand2")
        title_lbl.pack(anchor="w")
        # 点标题展开/收起详情
        title_lbl.bind("<Button-1>", lambda e: self._toggle_expand())

        # 类型小标签（habit / review）
        if ttype != "task":
            ttype_label = "🔁 习惯" if ttype == "habit" else "🔄 周期检查"
            tk.Label(title_frame, text=ttype_label,
                     font=(FONT_FAMILY, 10), bg=C.SURFACE, fg=C.TEXT_3
                     ).pack(anchor="w", pady=(2, 0))

        # 右侧 meta
        meta = tk.Frame(row1, bg=C.SURFACE)
        meta.pack(side="right", anchor="n")

        dl = task.get("deadline", "")
        dl_text, urgency = self.app._dl_label(dl)
        if dl_text:
            urgency_colors = {
                "overdue": C.DANGER, "today": C.WARNING,
                "soon": C.TEXT_2, "normal": C.TEXT_3,
            }
            tk.Label(meta, text=dl_text, font=(FONT_FAMILY, 11),
                     bg=C.SURFACE, fg=urgency_colors.get(urgency, C.TEXT_3)
                     ).pack(side="left", padx=(0, 6))

        # 操作按钮（极简图标）
        if self.in_today:
            star = HoverLabel(meta, text="★", command=lambda: self.app._remove_from_today(task),
                              bg=C.SURFACE, fg=C.WARNING, hover_bg=C.SURFACE, hover_fg=C.TEXT_3,
                              font=(FONT_DISPLAY, 14), padx=4)
        else:
            star = HoverLabel(meta, text="☆", command=lambda: self.app._add_to_today(task),
                              bg=C.SURFACE, fg=C.TEXT_3, hover_bg=C.SURFACE, hover_fg=C.WARNING,
                              font=(FONT_DISPLAY, 14), padx=4)
        star.pack(side="left")

        # 推迟按钮
        snooze = HoverLabel(meta, text="⏱", command=lambda: self._show_snooze_menu(),
                            bg=C.SURFACE, fg=C.TEXT_3, hover_bg=C.SURFACE, hover_fg=C.ACCENT,
                            font=(FONT_DISPLAY, 12), padx=4)
        snooze.pack(side="left")

        # 日历按钮
        cal = HoverLabel(meta, text="↗", command=lambda: self.app._sync_one(task),
                         bg=C.SURFACE, fg=C.TEXT_3, hover_bg=C.SURFACE, hover_fg=C.ACCENT,
                         font=(FONT_DISPLAY, 13), padx=4)
        cal.pack(side="left")

        # 第二行：next action
        action = task.get("next_action_5min", "")
        if action:
            tk.Label(self.wrap, text=action,
                     font=(FONT_FAMILY, 11),
                     bg=C.SURFACE, fg=C.TEXT_2,
                     anchor="w", justify="left",
                     wraplength=540
                     ).pack(fill="x", padx=(26, 0), pady=(4, 0))

        # 第三行：meta bits
        bits = []
        if task.get("domain") in DOMAIN_LABEL:
            bits.append(DOMAIN_LABEL[task["domain"]])
        subs = task.get("sub_tasks", [])
        if subs:
            done_n = sum(1 for s in subs if s.get("done"))
            bits.append(f"{done_n}/{len(subs)} 子任务")
        if ttype == "habit":
            streak = self._calc_streak(task)
            if streak > 0:
                bits.append(f"🔥 连续 {streak} 天")

        if bits:
            mr = tk.Frame(self.wrap, bg=C.SURFACE)
            mr.pack(fill="x", padx=(26, 0), pady=(6, 0))
            for i, b in enumerate(bits):
                if i > 0:
                    tk.Label(mr, text="·", font=(FONT_FAMILY, 10),
                             bg=C.SURFACE, fg=C.TEXT_3, padx=4).pack(side="left")
                tk.Label(mr, text=b, font=(FONT_FAMILY, 10),
                         bg=C.SURFACE, fg=C.TEXT_3).pack(side="left")

        # 展开区（子任务）
        self.expand_area = tk.Frame(self.wrap, bg=C.SURFACE)
        # 初始不显示

        # 卡片底部分隔线
        tk.Frame(self, bg=C.BORDER_SOFT, height=1).pack(fill="x")

    def _toggle_expand(self):
        if self._expanded:
            self.expand_area.pack_forget()
            self._expanded = False
        else:
            self._build_expand_area()
            self.expand_area.pack(fill="x", padx=(26, 0), pady=(10, 0))
            self._expanded = True

    def _build_expand_area(self):
        for w in self.expand_area.winfo_children():
            w.destroy()
        task = self.task

        # 子任务列表
        subs = task.get("sub_tasks", [])
        if subs:
            tk.Label(self.expand_area, text="子任务",
                     font=(FONT_FAMILY, 10, "bold"),
                     bg=C.SURFACE, fg=C.TEXT_3, anchor="w"
                     ).pack(fill="x", pady=(0, 4))
            for idx, sub in enumerate(subs):
                self._sub_row(self.expand_area, sub, idx)

        # 习惯打卡区
        if task.get("type") == "habit":
            tk.Label(self.expand_area, text="今日打卡",
                     font=(FONT_FAMILY, 10, "bold"),
                     bg=C.SURFACE, fg=C.TEXT_3, anchor="w"
                     ).pack(fill="x", pady=(8, 4))
            unit = task.get("habit_unit", "")
            checkin_row = tk.Frame(self.expand_area, bg=C.SURFACE)
            checkin_row.pack(fill="x", pady=(0, 4))

            val_entry = tk.Entry(checkin_row, font=(FONT_FAMILY, 12),
                                  bd=0, bg=C.SURFACE_2, fg=C.TEXT,
                                  relief="flat", width=10,
                                  insertbackground=C.TEXT)
            val_entry.pack(side="left", ipady=4, padx=(0, 6))
            if unit:
                tk.Label(checkin_row, text=unit, font=(FONT_FAMILY, 11),
                         bg=C.SURFACE, fg=C.TEXT_3).pack(side="left", padx=(0, 10))

            HoverLabel(checkin_row, text="打卡",
                       command=lambda: self._checkin(val_entry.get()),
                       bg=C.BRAND, fg=C.TEXT_INV,
                       hover_bg=C.BRAND_HOVER, hover_fg=C.TEXT_INV,
                       font=(FONT_FAMILY, 11, "bold"),
                       padx=14, pady=5
                       ).pack(side="left")

            # 最近打卡
            logs = task.get("weight_log", []) or task.get("checkin_log", [])
            if logs:
                recent = logs[-3:][::-1]
                rl = tk.Frame(self.expand_area, bg=C.SURFACE)
                rl.pack(fill="x", pady=(8, 0))
                for log in recent:
                    val = log.get("weight_kg") or log.get("value") or log.get("weight_jin")
                    tk.Label(rl,
                             text=f"  {log.get('date', '')}   {val} {unit}",
                             font=(FONT_FAMILY, 10),
                             bg=C.SURFACE, fg=C.TEXT_3, anchor="w"
                             ).pack(fill="x")

    def _sub_row(self, parent, sub, idx):
        row = tk.Frame(parent, bg=C.SURFACE)
        row.pack(fill="x", pady=2)

        done = sub.get("done", False)
        mark = "✓" if done else "○"
        color = C.SUCCESS if done else C.TEXT_3

        chk = tk.Label(row, text=mark, font=(FONT_DISPLAY, 12),
                       bg=C.SURFACE, fg=color, cursor="hand2", width=2)
        chk.pack(side="left")
        chk.bind("<Button-1>", lambda e: self._toggle_sub(idx))

        text = sub.get("title", "")
        fg = C.TEXT_3 if done else C.TEXT_2
        tk.Label(row, text=text, font=(FONT_FAMILY, 11),
                 bg=C.SURFACE, fg=fg, anchor="w", justify="left",
                 wraplength=460, cursor="hand2"
                 ).pack(side="left", fill="x", expand=True)

    def _toggle_sub(self, idx):
        try:
            data = load_todo()
            for t in data["待办"]:
                if t.get("id") == self.task.get("id"):
                    t["sub_tasks"][idx]["done"] = not t["sub_tasks"][idx].get("done", False)
                    sub_title = t["sub_tasks"][idx].get("title", "")
                    new_state = "完成" if t["sub_tasks"][idx]["done"] else "取消完成"
                    log_event("subtask_toggle",
                              detail=f"{new_state}: {sub_title}",
                              task_id=self.task.get("id"))
                    # 检查是否所有子任务都完成
                    all_done = all(s.get("done") for s in t["sub_tasks"])
                    self.task = t
                    if all_done and t.get("status") != "done":
                        save_todo(data)
                        self.app.load_data()
                        if messagebox.askyesno("子任务全部完成",
                            "所有子任务都已勾选。\n要把主任务也标记完成吗？"):
                            self.app._mark_done(self.task)
                            return
                    save_todo(data)
                    break
            self.app.load_data()
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def _checkin(self, value_str):
        try:
            value = float(value_str.strip())
        except ValueError:
            messagebox.showwarning("无效输入", "请输入数字")
            return
        try:
            data = load_todo()
            today = datetime.now().strftime("%Y-%m-%d")
            for t in data["待办"]:
                if t.get("id") == self.task.get("id"):
                    # 体重特殊处理
                    if "weight_log" in t or t.get("habit_unit") == "kg":
                        log = t.setdefault("weight_log", [])
                        log.append({
                            "date": today,
                            "weight_kg": value,
                            "weight_jin": round(value * 2, 1),
                            "note": "App打卡"
                        })
                    else:
                        log = t.setdefault("checkin_log", [])
                        log.append({"date": today, "value": value, "note": "App打卡"})
                    log_event("habit_checkin",
                              detail=f"{t.get('title', '')}: {value} {t.get('habit_unit', '')}",
                              task_id=self.task.get("id"))
                    break
            save_todo(data)
            self.app.load_data()
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def _calc_streak(self, task):
        """计算连续打卡天数"""
        logs = task.get("weight_log", []) or task.get("checkin_log", [])
        if not logs:
            return 0
        dates = sorted({log.get("date", "") for log in logs if log.get("date")}, reverse=True)
        if not dates:
            return 0
        try:
            today = date.today()
            streak = 0
            for i, d_str in enumerate(dates):
                d = datetime.strptime(d_str, "%Y-%m-%d").date()
                expected = today - timedelta(days=i)
                if d == expected or (i == 0 and d == today - timedelta(days=1)):
                    streak += 1
                else:
                    break
            return streak
        except Exception:
            return len(dates)

    def _show_snooze_menu(self):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="明天", command=lambda: self._snooze(1))
        menu.add_command(label="后天", command=lambda: self._snooze(2))
        menu.add_command(label="3 天后", command=lambda: self._snooze(3))
        menu.add_command(label="下周", command=lambda: self._snooze(7))
        menu.add_command(label="2 周后", command=lambda: self._snooze(14))
        menu.add_separator()
        menu.add_command(label="自定义...", command=self._snooze_custom)
        try:
            menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())
        finally:
            menu.grab_release()

    def _snooze(self, days):
        new_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        try:
            data = load_todo()
            for t in data["待办"]:
                if t.get("id") == self.task.get("id"):
                    old = t.get("deadline", "")
                    t["deadline"] = new_date
                    log_event("task_snooze",
                              detail=f"{t.get('title', '')}: {old} → {new_date}",
                              task_id=self.task.get("id"))
                    break
            save_todo(data)
            self.app.load_data()
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def _snooze_custom(self):
        new_date = simpledialog.askstring("自定义截止日期",
            "输入日期（如 2026-06-15）", parent=self.app.root)
        if not new_date:
            return
        try:
            datetime.strptime(new_date.strip(), "%Y-%m-%d")
        except Exception:
            messagebox.showwarning("格式错误", "请使用 YYYY-MM-DD 格式")
            return
        try:
            data = load_todo()
            for t in data["待办"]:
                if t.get("id") == self.task.get("id"):
                    old = t.get("deadline", "")
                    t["deadline"] = new_date.strip()
                    log_event("task_snooze",
                              detail=f"{t.get('title', '')}: {old} → {new_date}",
                              task_id=self.task.get("id"))
                    break
            save_todo(data)
            self.app.load_data()
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def _show_context_menu(self, event):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="编辑...", command=self._show_edit_dialog)
        menu.add_separator()
        menu.add_command(label="✓ 标记完成", command=lambda: self.app._mark_done(self.task))

        if self.in_today:
            menu.add_command(label="从今日移除", command=lambda: self.app._remove_from_today(self.task))
        else:
            menu.add_command(label="★ 加入今日", command=lambda: self.app._add_to_today(self.task))

        menu.add_separator()
        # 优先级子菜单
        pri_menu = tk.Menu(menu, tearoff=0)
        for p in PRIORITY_ORDER:
            pri_menu.add_command(
                label=f"{p}  {PRIORITY_CFG[p]['label']}",
                command=lambda pp=p: self._set_priority(pp))
        menu.add_cascade(label="优先级", menu=pri_menu)
        menu.add_command(label="推迟...", command=self._show_snooze_menu)
        menu.add_separator()
        menu.add_command(label="复制 ID", command=lambda: self._copy_to_clipboard(self.task.get("id", "")))
        menu.add_command(label="📅 同步到日历", command=lambda: self.app._sync_one(self.task))
        menu.add_separator()
        menu.add_command(label="✖ 删除（不可恢复）", command=self._delete_task)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _copy_to_clipboard(self, text):
        try:
            self.app.root.clipboard_clear()
            self.app.root.clipboard_append(text)
        except Exception:
            pass

    def _set_priority(self, p):
        try:
            data = load_todo()
            for t in data["待办"]:
                if t.get("id") == self.task.get("id"):
                    old = t.get("priority", "")
                    t["priority"] = p
                    log_event("task_edit",
                              detail=f"{t.get('title', '')}: priority {old} → {p}",
                              task_id=self.task.get("id"))
                    break
            save_todo(data)
            self.app.load_data()
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def _delete_task(self):
        if not messagebox.askyesno("确认删除",
            f"删除任务（不可恢复）：\n\n{self.task.get('title', '')}"):
            return
        try:
            data = load_todo()
            tid = self.task.get("id")
            data["待办"] = [t for t in data["待办"] if t.get("id") != tid]
            if tid in data.get("_today_focus", []):
                data["_today_focus"].remove(tid)
            log_event("task_delete",
                      detail=self.task.get("title", ""),
                      task_id=tid)
            save_todo(data)
            self.app.load_data()
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def _show_edit_dialog(self):
        dlg = tk.Toplevel(self.app.root)
        dlg.title("编辑任务")
        dlg.geometry("520x600")
        dlg.configure(bg=C.SURFACE)
        dlg.resizable(False, False)
        dlg.transient(self.app.root)
        dlg.grab_set()

        dlg.update_idletasks()
        x = self.app.root.winfo_x() + (self.app.root.winfo_width() - 520) // 2
        y = self.app.root.winfo_y() + 60
        dlg.geometry(f"+{x}+{y}")

        wrap = tk.Frame(dlg, bg=C.SURFACE, padx=32, pady=28)
        wrap.pack(fill="both", expand=True)

        tk.Label(wrap, text="编辑任务",
                 font=(FONT_DISPLAY, 22, "bold"),
                 bg=C.SURFACE, fg=C.TEXT, anchor="w"
                 ).pack(fill="x", pady=(0, 4))

        tk.Label(wrap, text=self.task.get("id", ""),
                 font=(FONT_FAMILY, 10),
                 bg=C.SURFACE, fg=C.TEXT_3, anchor="w"
                 ).pack(fill="x", pady=(0, 14))

        def field_label(text):
            tk.Label(wrap, text=text,
                     font=(FONT_FAMILY, 11, "bold"),
                     bg=C.SURFACE, fg=C.TEXT_2, anchor="w"
                     ).pack(fill="x", pady=(10, 4))

        def make_entry(initial):
            e = tk.Entry(wrap, font=(FONT_FAMILY, 13), bd=0,
                         bg=C.SURFACE_2, fg=C.TEXT, relief="flat",
                         insertbackground=C.TEXT)
            e.insert(0, initial)
            e.pack(fill="x", ipady=6)
            return e

        field_label("标题")
        title_entry = make_entry(self.task.get("title", ""))

        field_label("分类 / 优先级")
        row = tk.Frame(wrap, bg=C.SURFACE)
        row.pack(fill="x")
        cur_domain = DOMAIN_LABEL.get(self.task.get("domain", "work"), "工作")
        domain_var = tk.StringVar(value=cur_domain)
        ttk.Combobox(row, textvariable=domain_var,
                     values=list(DOMAIN_LABEL.values()),
                     state="readonly", font=(FONT_FAMILY, 12)
                     ).pack(side="left", fill="x", expand=True, ipady=4)
        tk.Frame(row, bg=C.SURFACE, width=10).pack(side="left")
        cur_pri = self.task.get("priority", "P1")
        pri_var = tk.StringVar(value=f"{cur_pri}  {PRIORITY_CFG.get(cur_pri, {}).get('label', '')}")
        ttk.Combobox(row, textvariable=pri_var,
                     values=["P0  今天", "P1  本周", "P2  本月", "P3  有空"],
                     state="readonly", font=(FONT_FAMILY, 12), width=12
                     ).pack(side="left", ipady=4)

        field_label("截止日期")
        dl_entry = make_entry(self.task.get("deadline", ""))

        field_label("下一步行动")
        action_entry = make_entry(self.task.get("next_action_5min", ""))

        field_label("备注")
        notes_text = tk.Text(wrap, font=(FONT_FAMILY, 12), bd=0,
                             bg=C.SURFACE_2, fg=C.TEXT, relief="flat",
                             height=4, wrap="word", insertbackground=C.TEXT)
        notes_text.insert("1.0", self.task.get("notes", ""))
        notes_text.pack(fill="x", ipady=6, pady=(0, 4))

        # 按钮区
        btn_row = tk.Frame(wrap, bg=C.SURFACE)
        btn_row.pack(fill="x", pady=(20, 0))

        def submit():
            new_title = title_entry.get().strip()
            if not new_title:
                title_entry.config(bg="#FEE2E2")
                return
            new_domain = "work"
            for k, v in DOMAIN_LABEL.items():
                if v == domain_var.get():
                    new_domain = k
                    break
            try:
                data = load_todo()
                for t in data["待办"]:
                    if t.get("id") == self.task.get("id"):
                        t["title"] = new_title
                        t["domain"] = new_domain
                        t["priority"] = pri_var.get().split()[0]
                        t["deadline"] = dl_entry.get().strip()
                        t["next_action_5min"] = action_entry.get().strip()
                        t["notes"] = notes_text.get("1.0", "end").strip()
                        log_event("task_edit",
                                  detail=f"{new_title} (edited)",
                                  task_id=self.task.get("id"))
                        break
                save_todo(data)
                dlg.destroy()
                self.app.load_data()
            except Exception as e:
                messagebox.showerror("错误", str(e), parent=dlg)

        HoverLabel(btn_row, text="取消",
                   bg=C.SURFACE, fg=C.TEXT_2,
                   hover_bg=C.SURFACE_2, hover_fg=C.TEXT,
                   font=(FONT_FAMILY, 12),
                   padx=18, pady=8,
                   command=dlg.destroy
                   ).pack(side="right", padx=(8, 0))

        HoverLabel(btn_row, text="保存",
                   bg=C.BRAND, fg=C.TEXT_INV,
                   hover_bg=C.BRAND_HOVER, hover_fg=C.TEXT_INV,
                   font=(FONT_FAMILY, 12, "bold"),
                   padx=22, pady=8,
                   command=submit
                   ).pack(side="right")

        dlg.bind("<Escape>", lambda e: dlg.destroy())


# ═══════════════════════════════════════
# 主应用
# ═══════════════════════════════════════
class TaskBoardApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Tasks")
        self.root.geometry("820x920")
        self.root.minsize(640, 520)
        self.root.configure(bg=C.BG)

        try:
            ttk.Style().theme_use("aqua")
        except Exception:
            pass

        self.tasks: list = []
        self.repay: list = []
        self.view: str = "today"  # today / all / done
        self._last_mtime: float = 0.0
        self._synced_ids: set = set()
        self._today_focus: list = []

        self._build_ui()
        self.load_data()
        self._poll()

    # ── 构建 ──────────────────────────
    def _build_ui(self):
        # ╭─ Header ─╮
        header = tk.Frame(self.root, bg=C.BG, padx=32, pady=22)
        header.pack(fill="x")

        title_row = tk.Frame(header, bg=C.BG)
        title_row.pack(fill="x")

        self._title_lbl = tk.Label(title_row, text="今天",
                                    font=(FONT_DISPLAY, 30, "bold"),
                                    bg=C.BG, fg=C.TEXT)
        self._title_lbl.pack(side="left")

        now = datetime.now()
        self._subtitle_lbl = tk.Label(title_row,
            text=f"  {now.month}月{now.day}日 · {WEEKDAYS[now.weekday()]}",
            font=(FONT_DISPLAY, 16),
            bg=C.BG, fg=C.TEXT_3)
        self._subtitle_lbl.pack(side="left", anchor="s", pady=(0, 6))

        # 右上操作
        actions = tk.Frame(title_row, bg=C.BG)
        actions.pack(side="right", anchor="s", pady=(0, 4))

        HoverLabel(actions, text="同步日历",
                   bg=C.BG, fg=C.TEXT_2,
                   hover_bg=C.SURFACE_2, hover_fg=C.TEXT,
                   font=(FONT_FAMILY, 12),
                   padx=10, pady=6,
                   command=self.sync_all
                   ).pack(side="left", padx=2)

        HoverLabel(actions, text="？",
                   bg=C.BG, fg=C.TEXT_3,
                   hover_bg=C.SURFACE_2, hover_fg=C.TEXT,
                   font=(FONT_FAMILY, 13, "bold"),
                   padx=10, pady=6,
                   command=self._show_help
                   ).pack(side="left", padx=2)

        HoverLabel(actions, text="＋  新任务",
                   bg=C.BRAND, fg=C.TEXT_INV,
                   hover_bg=C.BRAND_HOVER, hover_fg=C.TEXT_INV,
                   font=(FONT_FAMILY, 12, "bold"),
                   padx=16, pady=7,
                   command=self._show_add_dialog
                   ).pack(side="left", padx=(8, 0))

        # 统计行
        self._stats_label = tk.Label(header, text="",
                                      font=(FONT_FAMILY, 12),
                                      bg=C.BG, fg=C.TEXT_3, anchor="w")
        self._stats_label.pack(fill="x", pady=(8, 0))

        # ╭─ 搜索栏（默认隐藏，⌘F 显示） ─╮
        self._search_frame = tk.Frame(self.root, bg=C.BG, padx=32)
        # 不立刻 pack，由 _toggle_search 控制

        search_inner = tk.Frame(self._search_frame, bg=C.SURFACE_2)
        search_inner.pack(fill="x", pady=(4, 0))

        tk.Label(search_inner, text="🔍", font=(FONT_FAMILY, 12),
                 bg=C.SURFACE_2, fg=C.TEXT_3, padx=10
                 ).pack(side="left")

        self._search_var = tk.StringVar()
        self._search_entry = tk.Entry(search_inner, textvariable=self._search_var,
                                       font=(FONT_FAMILY, 13), bd=0,
                                       bg=C.SURFACE_2, fg=C.TEXT, relief="flat",
                                       insertbackground=C.TEXT)
        self._search_entry.pack(side="left", fill="x", expand=True, ipady=8)
        self._search_var.trace_add("write", lambda *a: self.load_data())

        HoverLabel(search_inner, text="✕",
                   bg=C.SURFACE_2, fg=C.TEXT_3,
                   hover_bg=C.SURFACE_2, hover_fg=C.TEXT,
                   font=(FONT_FAMILY, 12), padx=10,
                   command=self._toggle_search
                   ).pack(side="right")

        # ╭─ Tab 栏 ─╮
        tabs = tk.Frame(self.root, bg=C.BG, padx=32)
        tabs.pack(fill="x", pady=(4, 0))

        self._tab_btns = {}
        for key, label in [("today", "今天"), ("all", "全部"), ("done", "已完成")]:
            btn = tk.Label(tabs, text=label,
                           font=(FONT_FAMILY, 13, "bold"),
                           bg=C.BG, fg=C.TEXT_3, cursor="hand2",
                           padx=12, pady=8)
            btn.pack(side="left", padx=(0, 4))
            btn.bind("<Button-1>", lambda e, k=key: self._switch_view(k))
            self._tab_btns[key] = btn

        # 右侧：搜索图标
        search_icon = HoverLabel(tabs, text="🔍",
                                  bg=C.BG, fg=C.TEXT_3,
                                  hover_bg=C.SURFACE_2, hover_fg=C.TEXT,
                                  font=(FONT_FAMILY, 13), padx=10, pady=6,
                                  command=self._toggle_search)
        search_icon.pack(side="right")

        # tab 下分隔线
        tk.Frame(self.root, bg=C.BORDER, height=1).pack(fill="x", padx=32, pady=(0, 4))

        # ╭─ Banner 区（还款提醒） ─╮
        self._banner_holder = tk.Frame(self.root, bg=C.BG)
        self._banner_holder.pack(fill="x", padx=32, pady=(8, 0))

        # ╭─ 主内容 ─╮
        body = tk.Frame(self.root, bg=C.BG)
        body.pack(fill="both", expand=True, padx=24, pady=(8, 20))

        self._canvas = tk.Canvas(body, bg=C.BG, highlightthickness=0, bd=0)
        sb = ttk.Scrollbar(body, orient="vertical", command=self._canvas.yview)
        self._scroll = tk.Frame(self._canvas, bg=C.BG)

        self._scroll.bind("<Configure>",
                          lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.create_window((0, 0), window=self._scroll, anchor="nw", tags="sf")
        self._canvas.configure(yscrollcommand=sb.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._canvas.bind("<Configure>",
                          lambda e: self._canvas.itemconfig("sf", width=e.width))
        self._canvas.bind_all("<MouseWheel>",
                              lambda e: self._canvas.yview_scroll(-e.delta // 120, "units"))

        # ╭─ 键盘快捷键 ─╮
        self.root.bind_all("<Command-n>", lambda e: self._show_add_dialog())
        self.root.bind_all("<Command-N>", lambda e: self._show_add_dialog())
        self.root.bind_all("<Command-f>", lambda e: self._toggle_search())
        self.root.bind_all("<Command-F>", lambda e: self._toggle_search())
        self.root.bind_all("<Command-r>", lambda e: self.load_data())
        self.root.bind_all("<Command-R>", lambda e: self.load_data())
        self.root.bind_all("<Command-Key-1>", lambda e: self._switch_view("today"))
        self.root.bind_all("<Command-Key-2>", lambda e: self._switch_view("all"))
        self.root.bind_all("<Command-Key-3>", lambda e: self._switch_view("done"))
        self.root.bind("<Escape>", lambda e: self._toggle_search() if self._search_visible else None)

        self._search_visible = False

    def _toggle_search(self):
        if self._search_visible:
            self._search_frame.pack_forget()
            self._search_var.set("")
            self._search_visible = False
            self.load_data()
        else:
            # 在 tab 栏前显示搜索框
            self._search_frame.pack(fill="x", after=self._banner_holder)
            self._search_entry.focus_set()
            self._search_visible = True

    def _switch_view(self, view):
        self.view = view
        # 更新 tab 样式
        for k, btn in self._tab_btns.items():
            if k == view:
                btn.config(fg=C.TEXT)
            else:
                btn.config(fg=C.TEXT_3)
        # 更新标题
        titles = {"today": "今天", "all": "全部任务", "done": "已完成"}
        self._title_lbl.config(text=titles.get(view, "Tasks"))
        self.load_data()

    # ── 文件轮询 ──────────────────────
    def _poll(self):
        try:
            mtime = TODO_FILE.stat().st_mtime
            if self._last_mtime > 0 and mtime != self._last_mtime:
                self._last_mtime = mtime
                self.load_data()
            else:
                self._last_mtime = mtime
        except Exception:
            pass
        self.root.after(POLL_MS, self._poll)

    # ── 数据加载 ──────────────────────
    def load_data(self):
        for w in self._scroll.winfo_children():
            w.destroy()
        for w in self._banner_holder.winfo_children():
            w.destroy()

        try:
            data = load_todo()
        except Exception as e:
            messagebox.showerror("读取失败", str(e))
            return

        all_tasks = data.get("待办", [])
        active = [t for t in all_tasks if t.get("status") in ("todo", "doing", "blocked")]
        done = [t for t in all_tasks if t.get("status") == "done"]

        # today_focus 处理（如果跨天了清空）
        focus_date = data.get("_today_focus_date", "")
        today_str = datetime.now().strftime("%Y-%m-%d")
        if focus_date != today_str:
            data["_today_focus"] = []
            data["_today_focus_date"] = today_str
            save_todo(data)
        self._today_focus = data.get("_today_focus", [])

        # 自动注入 P0 + 今天截止的任务到 today_focus
        for t in active:
            tid = t.get("id", "")
            if tid in self._today_focus:
                continue
            urgency = self._dl_label(t.get("deadline", ""))[1]
            if t.get("priority") == "P0" or urgency in ("today", "overdue"):
                self._today_focus.append(tid)
        # 持久化
        if data.get("_today_focus") != self._today_focus:
            data["_today_focus"] = self._today_focus
            save_todo(data)

        # 搜索过滤
        query = self._search_var.get().strip().lower() if hasattr(self, '_search_var') else ""
        if query:
            def matches(t):
                hay = " ".join([
                    t.get("title", ""),
                    t.get("next_action_5min", ""),
                    t.get("notes", ""),
                    " ".join(t.get("tags", [])),
                    DOMAIN_LABEL.get(t.get("domain", ""), ""),
                ]).lower()
                return query in hay
            active = [t for t in active if matches(t)]
            done = [t for t in done if matches(t)]

        # 统计行
        overdue = sum(1 for t in active if self._dl_label(t.get("deadline", ""))[1] == "overdue")
        bits = [f"{len(active)} 项活跃"]
        if overdue:
            bits.append(f"⚠ {overdue} 项逾期")
        bits.append(f"{len(self._today_focus)} 项今日聚焦")
        if query:
            bits.append(f"🔍 搜索: {query}")
        self._stats_label.config(text="   ·   ".join(bits))

        # ── 还款 banner ──
        self._render_repay_banner()

        # ── 视图分发 ──
        if self.view == "today":
            self._render_today_view(active)
        elif self.view == "all":
            self._render_all_view(active)
        else:
            self._render_done_view(done)

    def _render_today_view(self, active):
        today_tasks = [t for t in active if t.get("id") in self._today_focus]
        other_tasks = [t for t in active if t.get("id") not in self._today_focus]

        if today_tasks:
            self._render_section("今日聚焦", today_tasks, in_today=True)
        else:
            empty = tk.Frame(self._scroll, bg=C.BG)
            empty.pack(fill="x", pady=40)
            tk.Label(empty, text="☆",
                     font=(FONT_DISPLAY, 36),
                     bg=C.BG, fg=C.TEXT_3).pack(pady=(0, 8))
            tk.Label(empty, text="今天没有聚焦任务",
                     font=(FONT_DISPLAY, 16, "bold"),
                     bg=C.BG, fg=C.TEXT_2).pack()
            tk.Label(empty, text="从下方任务列表点 ☆ 加入今日",
                     font=(FONT_FAMILY, 12),
                     bg=C.BG, fg=C.TEXT_3).pack(pady=(4, 0))

        # 其他任务（分组）
        if other_tasks:
            tk.Label(self._scroll, text="其他活跃任务",
                     font=(FONT_FAMILY, 12, "bold"),
                     bg=C.BG, fg=C.TEXT_3, anchor="w"
                     ).pack(fill="x", pady=(28, 8))
            self._render_by_priority(other_tasks, in_today=False)

    def _render_all_view(self, active):
        self._render_by_priority(active, in_today=False)
        if not active:
            tk.Label(self._scroll, text="✓  全部完成了",
                     font=(FONT_DISPLAY, 16),
                     bg=C.BG, fg=C.TEXT_3, pady=80).pack()

    def _render_done_view(self, done):
        # 按完成日期倒序
        done_sorted = sorted(done,
                              key=lambda t: t.get("_completed_at", ""),
                              reverse=True)
        # 取最近 30 项
        recent = done_sorted[:30]

        if not recent:
            tk.Label(self._scroll, text="还没有完成的任务",
                     font=(FONT_DISPLAY, 14),
                     bg=C.BG, fg=C.TEXT_3, pady=60).pack()
            return

        # 按日期分组
        groups = {}
        for t in recent:
            d = t.get("_completed_at", "")
            groups.setdefault(d, []).append(t)

        for date_key in sorted(groups.keys(), reverse=True):
            label = self._format_date_label(date_key)
            tk.Label(self._scroll, text=label,
                     font=(FONT_FAMILY, 12, "bold"),
                     bg=C.BG, fg=C.TEXT_3, anchor="w"
                     ).pack(fill="x", pady=(18, 6))

            container = tk.Frame(self._scroll, bg=C.SURFACE,
                                  highlightbackground=C.BORDER,
                                  highlightthickness=1)
            container.pack(fill="x")
            for t in groups[date_key]:
                self._done_card(container, t)

    def _done_card(self, parent, task):
        card = tk.Frame(parent, bg=C.SURFACE)
        card.pack(fill="x")
        wrap = tk.Frame(card, bg=C.SURFACE)
        wrap.pack(fill="x", padx=18, pady=10)

        row = tk.Frame(wrap, bg=C.SURFACE)
        row.pack(fill="x")

        tk.Label(row, text="✓", font=(FONT_DISPLAY, 14),
                 bg=C.SURFACE, fg=C.SUCCESS).pack(side="left", padx=(0, 10))

        title = task.get("title", "")
        tk.Label(row, text=title, font=(FONT_FAMILY, 12),
                 bg=C.SURFACE, fg=C.TEXT_2,
                 anchor="w", wraplength=520, justify="left"
                 ).pack(side="left", fill="x", expand=True)

        if task.get("domain") in DOMAIN_LABEL:
            tk.Label(row, text=DOMAIN_LABEL[task["domain"]],
                     font=(FONT_FAMILY, 10),
                     bg=C.SURFACE, fg=C.TEXT_3).pack(side="right")

        tk.Frame(card, bg=C.BORDER_SOFT, height=1).pack(fill="x")

    def _render_by_priority(self, tasks, in_today=False):
        for p in PRIORITY_ORDER:
            group = [t for t in tasks if t.get("priority") == p]
            if not group:
                continue
            self._render_section(PRIORITY_CFG[p]["label"], group, in_today=in_today,
                                  color=PRIORITY_CFG[p]["color"])

    def _render_section(self, label, tasks, in_today=False, color=None):
        hdr = tk.Frame(self._scroll, bg=C.BG)
        hdr.pack(fill="x", pady=(16, 6))

        if color:
            tk.Label(hdr, text="●", font=(FONT_DISPLAY, 10),
                     bg=C.BG, fg=color).pack(side="left", padx=(2, 8))

        tk.Label(hdr, text=label,
                 font=(FONT_FAMILY, 13, "bold"),
                 bg=C.BG, fg=C.TEXT).pack(side="left")

        tk.Label(hdr, text=f"  {len(tasks)}",
                 font=(FONT_FAMILY, 12),
                 bg=C.BG, fg=C.TEXT_3).pack(side="left")

        section = tk.Frame(self._scroll, bg=C.SURFACE,
                           highlightbackground=C.BORDER,
                           highlightthickness=1)
        section.pack(fill="x", pady=(0, 4))

        for t in tasks:
            TaskCard(section, t, self, in_today=in_today).pack(fill="x")

    # ── 还款 banner ──────────────────
    def _render_repay_banner(self):
        try:
            data = load_repay()
        except Exception:
            return

        upcoming = []
        now = datetime.now().date()
        for r in data.get("还款", []):
            if r.get("status") == "paid":
                continue
            try:
                d = datetime.strptime(r.get("due_date", ""), "%Y-%m-%d").date()
            except Exception:
                continue
            days = (d - now).days
            if -1 <= days <= 7:
                upcoming.append((days, r))

        if not upcoming:
            return

        upcoming.sort(key=lambda x: x[0])
        total = sum(r.get("amount", 0) for _, r in upcoming)

        banner = tk.Frame(self._banner_holder, bg=C.BANNER_BG,
                          highlightbackground=C.BANNER_BORDER,
                          highlightthickness=1)
        banner.pack(fill="x")

        inner = tk.Frame(banner, bg=C.BANNER_BG)
        inner.pack(fill="x", padx=16, pady=12)

        head = tk.Frame(inner, bg=C.BANNER_BG)
        head.pack(fill="x")

        tk.Label(head, text="💰  未来 7 天有 " + f"¥{total:,.0f} 待还（{len(upcoming)} 笔）",
                 font=(FONT_FAMILY, 12, "bold"),
                 bg=C.BANNER_BG, fg=C.BANNER_FG, anchor="w"
                 ).pack(side="left")

        # 详情区
        for days, r in upcoming[:3]:
            row = tk.Frame(inner, bg=C.BANNER_BG)
            row.pack(fill="x", pady=(4, 0))
            if days < 0:
                day_label = f"逾期 {-days} 天"
            elif days == 0:
                day_label = "今天"
            elif days == 1:
                day_label = "明天"
            else:
                day_label = f"{days} 天后"

            tk.Label(row, text=f"  · {r.get('title', '')}  ¥{r.get('amount', 0):,.0f}  ({day_label})",
                     font=(FONT_FAMILY, 11),
                     bg=C.BANNER_BG, fg=C.BANNER_FG, anchor="w"
                     ).pack(side="left", fill="x", expand=True)

    # ── Today 操作 ────────────────────
    def _add_to_today(self, task):
        tid = task.get("id")
        if tid in self._today_focus:
            return
        self._today_focus.append(tid)
        try:
            data = load_todo()
            data["_today_focus"] = self._today_focus
            data["_today_focus_date"] = datetime.now().strftime("%Y-%m-%d")
            save_todo(data)
            log_event("today_add", detail=task.get("title", ""), task_id=tid)
            self.load_data()
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def _remove_from_today(self, task):
        tid = task.get("id")
        if tid in self._today_focus:
            self._today_focus.remove(tid)
        try:
            data = load_todo()
            data["_today_focus"] = self._today_focus
            save_todo(data)
            log_event("today_remove", detail=task.get("title", ""), task_id=tid)
            self.load_data()
        except Exception as e:
            messagebox.showerror("错误", str(e))

    # ── 完成 ──────────────────────────
    def _mark_done(self, task):
        tid = task.get("id", "")
        title = task.get("title", "")
        if not messagebox.askyesno("标记完成", f"{title}"):
            return
        try:
            data = load_todo()
            today = datetime.now().strftime("%Y-%m-%d")
            for t in data["待办"]:
                if t.get("id") == tid:
                    t["status"] = "done"
                    t["_completed_at"] = today
                    t["_完成备注"] = t.get("_完成备注") or "App 标记完成"
                    for s in t.get("sub_tasks", []):
                        s["done"] = True
                    break
            # 从 today_focus 移除
            if tid in data.get("_today_focus", []):
                data["_today_focus"].remove(tid)
            save_todo(data)
            log_event("task_done", detail=title, task_id=tid)
            self.load_data()
        except Exception as e:
            messagebox.showerror("错误", str(e))

    # ── 新增 ──────────────────────────
    def _show_add_dialog(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("新任务")
        dlg.geometry("500x560")
        dlg.configure(bg=C.SURFACE)
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        dlg.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 500) // 2
        y = self.root.winfo_y() + 80
        dlg.geometry(f"+{x}+{y}")

        wrap = tk.Frame(dlg, bg=C.SURFACE, padx=32, pady=28)
        wrap.pack(fill="both", expand=True)

        tk.Label(wrap, text="新任务",
                 font=(FONT_DISPLAY, 22, "bold"),
                 bg=C.SURFACE, fg=C.TEXT, anchor="w"
                 ).pack(fill="x", pady=(0, 18))

        def field_label(text):
            tk.Label(wrap, text=text,
                     font=(FONT_FAMILY, 11, "bold"),
                     bg=C.SURFACE, fg=C.TEXT_2, anchor="w"
                     ).pack(fill="x", pady=(10, 4))

        def entry():
            e = tk.Entry(wrap, font=(FONT_FAMILY, 13), bd=0,
                         bg=C.SURFACE_2, fg=C.TEXT, relief="flat",
                         insertbackground=C.TEXT)
            e.pack(fill="x", ipady=6)
            return e

        field_label("标题")
        title_entry = entry()
        title_entry.focus()

        # 类型
        field_label("类型")
        type_var = tk.StringVar(value="task")
        type_row = tk.Frame(wrap, bg=C.SURFACE)
        type_row.pack(fill="x")
        for val, lbl in [("task", "一次性任务"), ("habit", "习惯打卡"), ("review", "周期检查")]:
            tk.Radiobutton(type_row, text=lbl, variable=type_var, value=val,
                           bg=C.SURFACE, fg=C.TEXT_2,
                           selectcolor=C.SURFACE,
                           font=(FONT_FAMILY, 11)
                           ).pack(side="left", padx=(0, 12))

        # 分类 + 优先级
        field_label("分类 / 优先级")
        row = tk.Frame(wrap, bg=C.SURFACE)
        row.pack(fill="x")

        domain_var = tk.StringVar(value="工作")
        ttk.Combobox(row, textvariable=domain_var,
                     values=list(DOMAIN_LABEL.values()),
                     state="readonly", font=(FONT_FAMILY, 12)
                     ).pack(side="left", fill="x", expand=True, ipady=4)

        tk.Frame(row, bg=C.SURFACE, width=10).pack(side="left")

        pri_var = tk.StringVar(value="P1  本周")
        ttk.Combobox(row, textvariable=pri_var,
                     values=["P0  今天", "P1  本周", "P2  本月", "P3  有空"],
                     state="readonly", font=(FONT_FAMILY, 12), width=12
                     ).pack(side="left", ipady=4)

        field_label("截止日期（YYYY-MM-DD，可空）")
        dl_entry = entry()

        field_label("下一步 5 分钟行动（可空）")
        action_entry = entry()

        # 今日勾选
        today_var = tk.IntVar(value=1)
        tk.Checkbutton(wrap, text="加入今日聚焦", variable=today_var,
                       bg=C.SURFACE, fg=C.TEXT_2,
                       selectcolor=C.SURFACE,
                       font=(FONT_FAMILY, 11)
                       ).pack(anchor="w", pady=(14, 0))

        # 按钮区
        btn_row = tk.Frame(wrap, bg=C.SURFACE)
        btn_row.pack(fill="x", pady=(24, 0))

        def submit():
            title = title_entry.get().strip()
            if not title:
                title_entry.config(bg="#FEE2E2")
                return
            domain_key = "work"
            for k, v in DOMAIN_LABEL.items():
                if v == domain_var.get():
                    domain_key = k
                    break
            try:
                data = load_todo()
                new_id = next_id(data)
                today = datetime.now().strftime("%Y-%m-%d")
                new_task = {
                    "id": new_id,
                    "title": title,
                    "domain": domain_key,
                    "type": type_var.get(),
                    "priority": pri_var.get().split()[0],
                    "status": "todo",
                    "created": today,
                    "deadline": dl_entry.get().strip() or "",
                    "next_action_5min": action_entry.get().strip() or "",
                    "notes": "",
                    "tags": ["App新增"],
                }
                data["待办"].append(new_task)
                if today_var.get():
                    data.setdefault("_today_focus", []).append(new_id)
                    data["_today_focus_date"] = today
                save_todo(data)
                log_event("task_create", detail=title, task_id=new_id)
                dlg.destroy()
                self.load_data()
            except Exception as e:
                messagebox.showerror("错误", str(e), parent=dlg)

        HoverLabel(btn_row, text="取消",
                   bg=C.SURFACE, fg=C.TEXT_2,
                   hover_bg=C.SURFACE_2, hover_fg=C.TEXT,
                   font=(FONT_FAMILY, 12),
                   padx=18, pady=8,
                   command=dlg.destroy
                   ).pack(side="right", padx=(8, 0))

        HoverLabel(btn_row, text="添加任务",
                   bg=C.BRAND, fg=C.TEXT_INV,
                   hover_bg=C.BRAND_HOVER, hover_fg=C.TEXT_INV,
                   font=(FONT_FAMILY, 12, "bold"),
                   padx=22, pady=8,
                   command=submit
                   ).pack(side="right")

        dlg.bind("<Return>", lambda e: submit())
        dlg.bind("<Escape>", lambda e: dlg.destroy())

    # ── 日历 ──────────────────────────
    def _sync_one(self, task):
        if not ensure_calendar():
            messagebox.showwarning("权限不足",
                "请到 系统设置 → 隐私与安全性 → 日历 中允许访问。")
            return
        ok, err = add_event(task)
        if ok:
            self._synced_ids.add(task.get("id", ""))
            log_event("calendar_sync", detail=task.get("title", ""), task_id=task.get("id"))
            messagebox.showinfo("已添加到日历",
                f"{task.get('title', '')}\n\n日历：{CALENDAR_NAME}")
        else:
            messagebox.showerror("同步失败", err)

    def sync_all(self):
        if not ensure_calendar():
            messagebox.showwarning("权限不足", "请允许日历访问")
            return
        targets = [t for t in self.tasks if t.get("deadline")]
        if not targets:
            try:
                data = load_todo()
                targets = [t for t in data.get("待办", [])
                           if t.get("status") in ("todo", "doing") and t.get("deadline")]
            except Exception:
                pass
        if not targets:
            messagebox.showinfo("提示", "没有带截止日期的任务可同步")
            return
        ok_count = 0
        for t in targets:
            ok, _ = add_event(t)
            if ok:
                ok_count += 1
                self._synced_ids.add(t.get("id", ""))
        messagebox.showinfo("同步完成", f"已同步 {ok_count} / {len(targets)} 到「{CALENDAR_NAME}」")

    # ── 工具 ──────────────────────────
    @staticmethod
    def _dl_label(s: str):
        s = (s or "").strip()
        if not s:
            return "", ""
        try:
            if " " in s:
                dt = datetime.strptime(s, "%Y-%m-%d %H:%M")
                has_time = True
            else:
                dt = datetime.strptime(s, "%Y-%m-%d").replace(hour=23, minute=59)
                has_time = False
        except Exception:
            return "", ""
        now = datetime.now()
        diff_days = (dt.date() - now.date()).days
        if dt < now and dt.date() < now.date():
            return f"逾期 {(now.date() - dt.date()).days} 天", "overdue"
        if diff_days == 0:
            label = "今天"
            if has_time:
                label += f" {dt.strftime('%H:%M')}"
            urg = "today" if dt > now else "overdue"
            return label, urg
        if diff_days == 1:
            return "明天", "soon"
        if 0 < diff_days <= 6:
            return WEEKDAYS[dt.weekday()], "soon"
        return f"{dt.month}月{dt.day}日", "normal"

    @staticmethod
    def _format_date_label(date_str: str) -> str:
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            today = date.today()
            diff = (today - d).days
            if diff == 0:
                return "今天"
            elif diff == 1:
                return "昨天"
            elif diff < 7:
                return f"{diff} 天前 · {WEEKDAYS[d.weekday()]}"
            else:
                return f"{d.month}月{d.day}日"
        except Exception:
            return date_str

    def _show_help(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("键盘快捷键")
        dlg.geometry("420x460")
        dlg.configure(bg=C.SURFACE)
        dlg.resizable(False, False)
        dlg.transient(self.root)

        dlg.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 420) // 2
        y = self.root.winfo_y() + 80
        dlg.geometry(f"+{x}+{y}")

        wrap = tk.Frame(dlg, bg=C.SURFACE, padx=32, pady=28)
        wrap.pack(fill="both", expand=True)

        tk.Label(wrap, text="键盘快捷键",
                 font=(FONT_DISPLAY, 22, "bold"),
                 bg=C.SURFACE, fg=C.TEXT, anchor="w"
                 ).pack(fill="x", pady=(0, 20))

        shortcuts = [
            ("⌘N", "新建任务"),
            ("⌘F", "搜索 / 收起搜索"),
            ("⌘R", "刷新数据"),
            ("⌘1", "今天视图"),
            ("⌘2", "全部视图"),
            ("⌘3", "已完成视图"),
            ("Esc", "关闭搜索框"),
            ("", ""),
            ("点标题", "展开/收起子任务"),
            ("右键", "编辑 / 优先级 / 删除"),
            ("点 ○", "标记完成"),
            ("点 ☆", "加入今日聚焦"),
            ("点 ⏱", "推迟到..."),
            ("点 ↗", "同步到日历"),
        ]

        for key, desc in shortcuts:
            if not key:
                tk.Frame(wrap, bg=C.SURFACE, height=10).pack(fill="x")
                continue
            row = tk.Frame(wrap, bg=C.SURFACE)
            row.pack(fill="x", pady=4)
            tk.Label(row, text=key, font=(FONT_FAMILY, 12, "bold"),
                     bg=C.SURFACE_2, fg=C.TEXT,
                     padx=10, pady=4, width=8
                     ).pack(side="left")
            tk.Label(row, text=desc, font=(FONT_FAMILY, 12),
                     bg=C.SURFACE, fg=C.TEXT_2,
                     padx=12
                     ).pack(side="left")

        dlg.bind("<Escape>", lambda e: dlg.destroy())

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    TaskBoardApp().run()
