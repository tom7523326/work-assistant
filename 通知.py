#!/usr/bin/env python3
"""
每日通知脚本
══════════════
读取 12_待办.json + 14_还款日历.json，生成 macOS 通知。

被 LaunchAgent 定时触发：
- 08:00 晨间提醒
- 11:00 上午检查
- 18:00 下午检查
- 21:00 晚间复盘提醒
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, date, timedelta

BASE_DIR = Path(__file__).resolve().parent
TODO_FILE = BASE_DIR / "数据" / "12_待办.json"
REPAY_FILE = BASE_DIR / "数据" / "14_还款日历.json"


def osa_notify(title: str, subtitle: str, message: str, sound: str = "default"):
    """通过 osascript 发送 macOS 通知"""
    title = title.replace('"', "'")
    subtitle = subtitle.replace('"', "'")
    message = message.replace('"', "'")
    script = f'''
display notification "{message}" with title "{title}" subtitle "{subtitle}" sound name "{sound}"
'''
    subprocess.run(["osascript", "-e", script], capture_output=True)


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


def morning_brief():
    """08:00 晨间简报"""
    data = load_json(TODO_FILE)
    repay = load_json(REPAY_FILE) or {"还款": []}
    if not data:
        return

    active = [t for t in data.get("待办", [])
              if t.get("status") in ("todo", "doing", "blocked")]

    focus_ids = data.get("_today_focus", [])
    focus = [t for t in active if t.get("id") in focus_ids]

    today = date.today()
    overdue = []
    for t in active:
        dl = _dl_parse(t.get("deadline", ""))
        if dl and dl.date() < today:
            overdue.append(t)

    # 还款（未来 3 天）
    upcoming_repay = []
    for r in repay.get("还款", []):
        if r.get("status") == "paid":
            continue
        d = _dl_parse(r.get("due_date", ""))
        if d:
            days = (d.date() - today).days
            if -1 <= days <= 3:
                upcoming_repay.append((days, r))

    # 组装消息
    parts = []
    if focus:
        parts.append(f"今日聚焦 {len(focus)} 项")
    if overdue:
        parts.append(f"⚠️ 逾期 {len(overdue)} 项")
    if upcoming_repay:
        total = sum(r.get("amount", 0) for _, r in upcoming_repay)
        parts.append(f"💰 3天内还款 ¥{total:,.0f}")

    if not parts:
        message = "今天没有紧急任务，加油！"
    else:
        message = "  ·  ".join(parts)

    weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][today.weekday()]
    osa_notify(
        title="☀️ 早安",
        subtitle=f"{today.month}月{today.day}日 · {weekday}",
        message=message,
    )


def midday_check():
    """11:00 上午检查"""
    data = load_json(TODO_FILE)
    if not data:
        return

    focus_ids = data.get("_today_focus", [])
    active = [t for t in data.get("待办", [])
              if t.get("status") in ("todo", "doing", "blocked")]
    pending_focus = [t for t in active if t.get("id") in focus_ids]

    if not pending_focus:
        return

    # 取第一个未完成的
    top = pending_focus[0]
    osa_notify(
        title="⏰ 上午检查",
        subtitle=f"今日还有 {len(pending_focus)} 项",
        message=top.get("title", "")[:60],
    )


def afternoon_check():
    """18:00 下午检查"""
    data = load_json(TODO_FILE)
    repay = load_json(REPAY_FILE) or {"还款": []}
    if not data:
        return

    focus_ids = data.get("_today_focus", [])
    active = [t for t in data.get("待办", [])
              if t.get("status") in ("todo", "doing", "blocked")]
    pending = [t for t in active if t.get("id") in focus_ids]

    # 明天的还款
    tomorrow = date.today() + timedelta(days=1)
    tom_repay = []
    for r in repay.get("还款", []):
        if r.get("status") == "paid":
            continue
        d = _dl_parse(r.get("due_date", ""))
        if d and d.date() == tomorrow:
            tom_repay.append(r)

    msg_parts = []
    if pending:
        msg_parts.append(f"还有 {len(pending)} 项今日聚焦未完成")
    if tom_repay:
        total = sum(r.get("amount", 0) for r in tom_repay)
        msg_parts.append(f"明天还款 ¥{total:,.0f}（{len(tom_repay)} 笔）")

    if not msg_parts:
        return

    osa_notify(
        title="🌆 下午检查",
        subtitle="还来得及",
        message="  ·  ".join(msg_parts),
    )


def evening_review():
    """21:00 晚间复盘提醒"""
    data = load_json(TODO_FILE)
    if not data:
        return

    # 今天完成的
    today_str = date.today().strftime("%Y-%m-%d")
    done_today = [t for t in data.get("待办", [])
                  if t.get("status") == "done"
                  and t.get("_completed_at") == today_str]

    focus_ids = data.get("_today_focus", [])
    active = [t for t in data.get("待办", [])
              if t.get("status") in ("todo", "doing", "blocked")]
    pending = [t for t in active if t.get("id") in focus_ids]

    msg = f"今天完成 {len(done_today)} 项"
    if pending:
        msg += f"，还有 {len(pending)} 项未完成"

    osa_notify(
        title="🌙 晚间复盘",
        subtitle="今天怎么样",
        message=msg + "，跟 AI 聊聊吧",
    )


def test_notify():
    """测试通知是否工作"""
    osa_notify("🧪 测试通知", "工作助手", "如果你看到这条，通知系统正常")


COMMANDS = {
    "morning": morning_brief,
    "midday": midday_check,
    "afternoon": afternoon_check,
    "evening": evening_review,
    "test": test_notify,
}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "test"
    fn = COMMANDS.get(cmd)
    if not fn:
        print(f"用法: python3 通知.py [{'/'.join(COMMANDS.keys())}]")
        sys.exit(1)
    fn()
