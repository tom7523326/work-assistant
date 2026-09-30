#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_index.py — 工作助手主入口（驾驶舱）

聚合 4 大模块的核心 KPI + 跨模块关键节点时间轴。
数据基准日 2026-05-15，但运行时显示当天日期。

使用：python3 build_index.py
"""
import json
from pathlib import Path
from datetime import date, datetime, timedelta

ROOT = Path(__file__).parent
DATA = ROOT / "数据"
TODAY = date.today()
WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def load_json(name):
    try:
        return json.loads((DATA / name).read_text(encoding="utf-8"))
    except Exception as e:
        return {"_error": str(e)}


# ============ 加载所有数据源 ============
huizong = load_json("00_汇总.json")
shouru = load_json("01_收入.json")
daikuan = load_json("02_贷款.json")
xinyongka = load_json("03_信用卡.json")
todo = load_json("12_待办.json")
contacts = load_json("14_人脉.json")
gangwei = load_json("08_岗位与履历.json")
guihua = load_json("11_职业规划.json")


# ============ KPI 计算 ============

# === 1. 待办 KPI ===
todo_active = [t for t in todo.get("待办", []) if t.get("status") in ("todo", "doing")]
todo_done = [t for t in todo.get("待办", []) if t.get("status") == "done"]


def parse_ddl(s):
    if not s: return None
    try:
        return datetime.strptime(s.split()[0], "%Y-%m-%d").date()
    except:
        return None


todo_overdue = []
todo_today = []
todo_thisweek = []
todo_later = []

for t in todo_active:
    d = parse_ddl(t.get("deadline", ""))
    if d is None:
        todo_later.append(t)
    elif d < TODAY:
        todo_overdue.append(t)
    elif d == TODAY:
        todo_today.append(t)
    elif (d - TODAY).days <= 7:
        todo_thisweek.append(t)
    else:
        todo_later.append(t)

# 7 天内完成数
done_recent = 0
for t in todo_done:
    d = t.get("_completed_at", "")
    try:
        cd = datetime.strptime(d, "%Y-%m-%d").date()
        if (TODAY - cd).days <= 7:
            done_recent += 1
    except:
        pass

# === 2. 财务 KPI ===
zichan = huizong.get("资产负债表_快照", {})
xianjin = huizong.get("现金流_月", {})
yujing = huizong.get("关键比率_预警", {})

net_assets = zichan.get("净资产", 0)
total_assets = zichan.get("总资产", 0)
total_debt = zichan.get("总负债", 0)
month_save = xianjin.get("净储蓄能力_月_非奖金", 0)
emergency_ratio = yujing.get("紧急储备金覆盖_月", 0)
if isinstance(emergency_ratio, str):
    try:
        emergency_ratio = float(emergency_ratio.replace("月","").strip())
    except:
        emergency_ratio = 0

# === 3. 工作 KPI ===
gw_info = gangwei.get("当前岗位", {})
job_level = gw_info.get("职级", "未填写")
work_age = gw_info.get("司龄_年", 14.6)
perf_count = len(gangwei.get("绩效汇总_腾讯7次评估", []))

# 项目数（从 todo 里数 work domain 的活跃任务）
work_active = [t for t in todo_active if t.get("domain") == "work"]
project_count_estimate = 5  # 5 个甲方项目（成都/农广校/广东/浙江/西双版纳）

# === 4. 人脉 KPI ===
contacts_list = contacts.get("联系人", [])
contacts_count = len(contacts_list)

# 即将见面（next_meeting 字段在未来）
upcoming_meet = []
need_reach = []  # 距上次见面 ≥3 个月
import re
for c in contacts_list:
    nm = c.get("下次见面计划", "")
    if isinstance(nm, str) and nm:
        # 提取日期 YYYY-MM-DD
        m = re.match(r"(\d{4}-\d{2}-\d{2})", nm)
        if m:
            d = parse_ddl(m.group(1))
            if d and d >= TODAY:
                upcoming_meet.append((c, d, nm))
    elif isinstance(nm, dict) and nm.get("日期"):
        d = parse_ddl(nm["日期"])
        if d and d >= TODAY:
            upcoming_meet.append((c, d, nm.get("类型", "见面")))


# ============ 跨模块时间轴 ============
events = []

# 来自 todo 看板的 deadline
for t in todo_active:
    d = parse_ddl(t.get("deadline", ""))
    if d and TODAY <= d <= TODAY + timedelta(days=45):
        events.append({
            "date": d,
            "title": t["title"],
            "source": "todo",
            "domain": t.get("domain", ""),
            "id": t["id"],
        })

# 来自 00_汇总.json 的本月重要事项
for ev in huizong.get("本月_5月_重要事项", []):
    d = parse_ddl(ev.get("日期", ""))
    if d and TODAY <= d <= TODAY + timedelta(days=45):
        events.append({
            "date": d,
            "title": ev.get("事项", ""),
            "source": "财务",
            "domain": "finance",
            "amount": ev.get("金额", ""),
        })

# 来自 02_贷款.json 的关键节点
for ev in daikuan.get("_重要节点提醒", []):
    d = parse_ddl(ev.get("日期", ""))
    if d and TODAY <= d <= TODAY + timedelta(days=45):
        events.append({
            "date": d,
            "title": ev.get("事项", ""),
            "source": "贷款",
            "domain": "finance",
            "amount": ev.get("金额", ""),
        })

# 来自 03_信用卡.json 的提醒
for ev in xinyongka.get("_提醒事项", []):
    if "日期" not in ev: continue
    d = parse_ddl(ev["日期"])
    if d and TODAY <= d <= TODAY + timedelta(days=45):
        events.append({
            "date": d,
            "title": ev.get("事项", ""),
            "source": "信用卡",
            "domain": "finance",
        })

# 人脉
for c, d, label in upcoming_meet:
    if d <= TODAY + timedelta(days=45):
        events.append({
            "date": d,
            "title": f"{c['姓名']} · {label[:20]}",
            "source": "人脉",
            "domain": "social",
        })

# 去重 + 排序
seen = set()
unique_events = []
for ev in sorted(events, key=lambda x: (x["date"], x["title"])):
    key = (ev["date"], ev["title"])
    if key in seen: continue
    seen.add(key)
    unique_events.append(ev)


# ============ HTML 渲染 ============
def fmt_money(n):
    if n >= 10000:
        return f"¥{n/10000:.1f}万"
    return f"¥{n:,.0f}"


def days_until(d):
    delta = (d - TODAY).days
    if delta == 0: return "今天"
    if delta == 1: return "明天"
    if delta < 0: return f"已过 {-delta} 天"
    if delta <= 7: return f"{delta} 天后"
    return d.strftime("%-m/%-d")


hour = datetime.now().hour
if hour < 11:
    greeting = "早上好"
elif hour < 14:
    greeting = "中午好"
elif hour < 18:
    greeting = "下午好"
else:
    greeting = "晚上好"

now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
weekday_str = WEEKDAY_CN[TODAY.weekday()]

# 人名（从 SOUL 提示）
user_name = "寿麟"


# 顶部状态条文案
if len(todo_overdue) > 0:
    status_line = f"⚠️ {len(todo_overdue)} 件已过期 · 今天 {len(todo_today)} 件 · 本周 {len(todo_thisweek)} 件"
elif len(todo_today) > 0:
    status_line = f"今天必动 {len(todo_today)} 件 · 本周还有 {len(todo_thisweek)} 件 · 7 天内已完成 {done_recent} 件"
else:
    status_line = f"今天没有硬截止 · 本周 {len(todo_thisweek)} 件 · 7 天内已完成 {done_recent} 件"


# === 渲染时间轴 ===
def render_timeline():
    if not unique_events:
        return '<div class="empty">未来 45 天内没有关键节点</div>'
    parts = []
    last_date = None
    for ev in unique_events:
        d = ev["date"]
        wd = WEEKDAY_CN[d.weekday()]
        domain_color = {
            "finance": "#d4af37",
            "family": "#a78bfa",
            "work": "#60a5fa",
            "social": "#10b981",
            "life": "#34d399",
            "growth": "#fb923c",
        }.get(ev.get("domain", ""), "#8b94a7")
        amount_html = f'<span class="ev-amount">{ev.get("amount","")}</span>' if ev.get("amount") else ""
        urgent = (d - TODAY).days <= 3
        urgent_cls = " urgent" if urgent else ""
        parts.append(f'''
<div class="ev-row{urgent_cls}">
  <div class="ev-date">
    <div class="ev-day">{d.strftime("%-m/%-d")}</div>
    <div class="ev-wd">{wd}</div>
    <div class="ev-rel">{days_until(d)}</div>
  </div>
  <div class="ev-dot" style="background:{domain_color}"></div>
  <div class="ev-body">
    <div class="ev-title">{ev["title"]}</div>
    <div class="ev-meta"><span class="ev-source">{ev["source"]}</span>{amount_html}</div>
  </div>
</div>''')
    return "\n".join(parts)


timeline_html = render_timeline()


# === 卡片：今日待办 ===
todo_card = f'''
<a href="今日待办.html" class="card card-todo">
  <div class="card-head">
    <div class="card-title">📋 今日待办</div>
    <div class="card-arrow">→</div>
  </div>
  <div class="card-kpis">
    <div class="kpi"><div class="kpi-num overdue">{len(todo_overdue)}</div><div class="kpi-lbl">已过期</div></div>
    <div class="kpi"><div class="kpi-num today">{len(todo_today)}</div><div class="kpi-lbl">今天</div></div>
    <div class="kpi"><div class="kpi-num">{len(todo_thisweek)}</div><div class="kpi-lbl">本周</div></div>
    <div class="kpi"><div class="kpi-num done">{len(todo_done)}</div><div class="kpi-lbl">已完成</div></div>
  </div>
  <div class="card-foot">{len(todo_active)} 件待办 · 7 天内完成 {done_recent} 件</div>
</a>'''


# === 卡片：财务总览 ===
emer_color = "#ff5d5d" if emergency_ratio < 1.5 else ("#ffd95d" if emergency_ratio < 3 else "#7dd3a8")
finance_card = f'''
<a href="财务总览.html" class="card card-finance">
  <div class="card-head">
    <div class="card-title">💰 财务总览</div>
    <div class="card-arrow">→</div>
  </div>
  <div class="card-kpis">
    <div class="kpi"><div class="kpi-num">{fmt_money(net_assets)}</div><div class="kpi-lbl">净资产</div></div>
    <div class="kpi"><div class="kpi-num">{fmt_money(month_save)}</div><div class="kpi-lbl">月净储蓄</div></div>
    <div class="kpi"><div class="kpi-num" style="color:{emer_color}">{emergency_ratio:.2f}</div><div class="kpi-lbl">紧急金(月)</div></div>
    <div class="kpi"><div class="kpi-num">{fmt_money(total_debt)}</div><div class="kpi-lbl">总负债</div></div>
  </div>
  <div class="card-foot">总资产 {fmt_money(total_assets)} · 数据基准 {huizong.get("_数据基准日","2026-05-15")}</div>
</a>'''


# === 卡片：工作总览 ===
work_card = f'''
<a href="工作总览.html" class="card card-work">
  <div class="card-head">
    <div class="card-title">💼 工作总览</div>
    <div class="card-arrow">→</div>
  </div>
  <div class="card-kpis">
    <div class="kpi"><div class="kpi-num">{job_level}</div><div class="kpi-lbl">职级</div></div>
    <div class="kpi"><div class="kpi-num">{work_age}</div><div class="kpi-lbl">司龄(年)</div></div>
    <div class="kpi"><div class="kpi-num">{project_count_estimate}</div><div class="kpi-lbl">在做项目</div></div>
    <div class="kpi"><div class="kpi-num">{len(work_active)}</div><div class="kpi-lbl">工作待办</div></div>
  </div>
  <div class="card-foot">绩效 {perf_count} 次 · 主线：5 个甲方项目并行</div>
</a>'''


# === 卡片：人脉档案 ===
upcoming_count = len(upcoming_meet)
contacts_card = f'''
<a href="人脉档案.html" class="card card-contacts">
  <div class="card-head">
    <div class="card-title">📇 人脉档案</div>
    <div class="card-arrow">→</div>
  </div>
  <div class="card-kpis">
    <div class="kpi"><div class="kpi-num">{contacts_count}</div><div class="kpi-lbl">联系人</div></div>
    <div class="kpi"><div class="kpi-num upcoming">{upcoming_count}</div><div class="kpi-lbl">即将见面</div></div>
    <div class="kpi"><div class="kpi-num">0</div><div class="kpi-lbl">该联系了</div></div>
    <div class="kpi"><div class="kpi-num">0</div><div class="kpi-lbl">本月互动</div></div>
  </div>
  <div class="card-foot">{"📅 " + upcoming_meet[0][0]["姓名"] + " · " + upcoming_meet[0][1].strftime("%-m/%-d") if upcoming_meet else "数据库刚建立，慢慢积累"}</div>
</a>'''


# === 数据/记忆 入口 ===
data_entries = '''
<a href="数据/" class="data-entry"><div>📊</div><div>数据</div></a>
<a href="财务/" class="data-entry"><div>💰</div><div>财务原档</div></a>
<a href="工作/" class="data-entry"><div>💼</div><div>工作原档</div></a>
<a href="投资/" class="data-entry"><div>📈</div><div>投资</div></a>
<a href="AI学习/" class="data-entry"><div>🤖</div><div>AI 学习</div></a>
<a href="_记忆/" class="data-entry"><div>🧠</div><div>记忆系统</div></a>
'''


HTML = f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>工作助手 · 个人作战中心</title>
<style>
:root{{
  --bg:#0f1115; --panel:#171a21; --panel2:#1c2029; --panel3:#22262f;
  --border:#2a2f3a; --border-hi:#3a4050;
  --text:#e6e8ee; --muted:#8b94a7; --dim:#5a6477;
  --accent:#7c9eff;
  --p0:#ff5d5d; --p1:#ffa45d; --p2:#ffd95d; --p3:#7dd3a8;
  --c-finance:#d4af37; --c-family:#a78bfa; --c-work:#60a5fa;
  --c-social:#10b981; --c-life:#34d399; --c-growth:#fb923c;
}}
*{{box-sizing:border-box;margin:0;padding:0;}}
html,body{{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Helvetica Neue",Arial,sans-serif;
  background:var(--bg);color:var(--text);line-height:1.55;}}
body{{padding:32px 40px 80px;max-width:1280px;margin:0 auto;}}
a{{color:inherit;text-decoration:none;}}

/* ========== 顶部 ========== */
.head{{display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:8px;flex-wrap:wrap;gap:12px;}}
.head h1{{font-size:28px;font-weight:600;letter-spacing:-0.5px;}}
.head h1 .greeting{{color:var(--accent);}}
.head .now{{color:var(--muted);font-size:14px;}}
.status-line{{font-size:14px;color:var(--muted);margin-bottom:32px;padding-bottom:16px;border-bottom:1px solid var(--border);}}
.status-line strong{{color:var(--text);}}

/* ========== 4 大卡片 ========== */
.cards{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-bottom:36px;}}
.card{{display:block;background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:20px 22px;
  transition:all 0.2s;cursor:pointer;position:relative;overflow:hidden;}}
.card::before{{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--accent);}}
.card-todo::before{{background:var(--p1);}}
.card-finance::before{{background:var(--c-finance);}}
.card-work::before{{background:var(--c-work);}}
.card-contacts::before{{background:var(--c-social);}}
.card:hover{{background:var(--panel2);border-color:var(--border-hi);transform:translateY(-1px);}}
.card-head{{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px;}}
.card-title{{font-size:17px;font-weight:600;}}
.card-arrow{{color:var(--dim);font-size:18px;transition:transform 0.2s;}}
.card:hover .card-arrow{{color:var(--accent);transform:translateX(3px);}}
.card-kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:14px;}}
.kpi{{text-align:center;background:var(--panel2);border-radius:8px;padding:10px 4px;}}
.kpi-num{{font-size:20px;font-weight:700;line-height:1.2;color:var(--text);}}
.kpi-num.overdue{{color:var(--p0);}}
.kpi-num.today{{color:var(--p1);}}
.kpi-num.done{{color:var(--p3);}}
.kpi-num.upcoming{{color:var(--c-social);}}
.kpi-lbl{{font-size:11px;color:var(--muted);margin-top:3px;}}
.card-foot{{font-size:12px;color:var(--muted);padding-top:12px;border-top:1px solid var(--border);}}

/* ========== 时间轴 ========== */
.section-title{{font-size:13px;font-weight:600;color:var(--muted);letter-spacing:1px;
  margin:36px 0 14px;text-transform:uppercase;display:flex;align-items:center;gap:10px;}}
.section-title::after{{content:"";flex:1;height:1px;background:var(--border);}}
.timeline{{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:8px 0;}}
.ev-row{{display:grid;grid-template-columns:90px 16px 1fr;gap:14px;align-items:center;
  padding:14px 22px;border-bottom:1px solid var(--border);}}
.ev-row:last-child{{border-bottom:0;}}
.ev-row:hover{{background:var(--panel2);}}
.ev-row.urgent{{background:linear-gradient(90deg,rgba(255,93,93,0.05),transparent 30%);}}
.ev-date{{text-align:center;}}
.ev-day{{font-size:18px;font-weight:600;color:var(--text);}}
.ev-wd{{font-size:11px;color:var(--muted);margin-top:2px;}}
.ev-rel{{font-size:10px;color:var(--dim);margin-top:2px;}}
.ev-row.urgent .ev-rel{{color:var(--p0);font-weight:600;}}
.ev-dot{{width:10px;height:10px;border-radius:50%;justify-self:center;}}
.ev-body{{display:flex;justify-content:space-between;align-items:center;}}
.ev-title{{font-size:14px;color:var(--text);}}
.ev-meta{{display:flex;gap:8px;align-items:center;font-size:11px;}}
.ev-source{{background:var(--panel3);color:var(--muted);padding:2px 8px;border-radius:3px;}}
.ev-amount{{color:var(--c-finance);font-weight:600;}}
.empty{{text-align:center;color:var(--dim);padding:24px;font-size:13px;}}

/* ========== 数据入口 ========== */
.data-entries{{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;}}
.data-entry{{background:var(--panel);border:1px solid var(--border);border-radius:10px;
  padding:18px 12px;text-align:center;font-size:12px;color:var(--muted);transition:all 0.2s;}}
.data-entry div:first-child{{font-size:24px;margin-bottom:6px;}}
.data-entry:hover{{background:var(--panel2);border-color:var(--border-hi);color:var(--text);}}

.footer{{margin-top:48px;padding-top:20px;border-top:1px solid var(--border);
  font-size:11px;color:var(--dim);text-align:center;line-height:1.8;}}
.footer code{{background:var(--panel2);padding:2px 6px;border-radius:3px;color:var(--accent);}}

@media (max-width:900px){{
  body{{padding:18px;}}
  .cards{{grid-template-columns:1fr;}}
  .data-entries{{grid-template-columns:repeat(3,1fr);}}
  .ev-row{{grid-template-columns:70px 12px 1fr;padding:12px;}}
}}
</style>
</head>
<body>

<div class="head">
  <h1><span class="greeting">{greeting}</span>，{user_name}</h1>
  <div class="now">{TODAY.strftime("%Y-%m-%d")} {weekday_str} · {now_str.split()[1]}</div>
</div>
<div class="status-line">{status_line}</div>

<div class="cards">
  {todo_card}
  {finance_card}
  {work_card}
  {contacts_card}
</div>

<div class="section-title">🔥 未来 45 天关键节点</div>
<div class="timeline">
{timeline_html}
</div>

<div class="section-title">📁 数据与记忆</div>
<div class="data-entries">
{data_entries}
</div>

<div class="footer">
  工作助手 · 个人作战中心 · 数据基准 {huizong.get("_数据基准日","2026-05-15")}<br>
  入口：<code>index.html</code> · 重新生成：<code>python3 build_index.py</code><br>
  四大模块：今日待办 / 财务总览 / 工作总览 / 人脉档案
</div>

</body>
</html>
'''

(ROOT / "index.html").write_text(HTML, encoding="utf-8")
print(f"✅ index.html 已生成")
print(f"   - 待办：{len(todo_active)} 活跃 / {len(todo_done)} 已完成")
print(f"   - 财务：净资产 {fmt_money(net_assets)} / 月净储 {fmt_money(month_save)}")
print(f"   - 工作：{job_level} · {project_count_estimate} 个项目")
print(f"   - 人脉：{contacts_count} 人 / {upcoming_count} 即将见面")
print(f"   - 时间轴：{len(unique_events)} 个未来 45 天节点")
