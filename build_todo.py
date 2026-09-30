"""
待办看板 v3：信息全可见，零隐藏
设计原则（从 v2 倒过来）：
  1. 默认全展开 —— 用户要看到全貌
  2. "已完成"区独立大区，完成备注完整显示
  3. 视图切换：时间分桶 / 全部列表 / 仅活跃 / 仅已完成
  4. 顶部"本周战况" —— 一眼看到一周状态
"""
import json
from pathlib import Path
from datetime import datetime, date, timedelta

ROOT = Path(__file__).resolve().parent
data = json.loads((ROOT / '数据' / '12_待办.json').read_text(encoding='utf-8'))

DOMAIN_META = {
    "family":  {"emoji": "👨‍👩‍👧", "name": "家庭", "color": "#a78bfa", "bg": "rgba(167,139,250,0.10)"},
    "work":    {"emoji": "💼", "name": "工作", "color": "#60a5fa", "bg": "rgba(96,165,250,0.10)"},
    "finance": {"emoji": "💰", "name": "财务", "color": "#fbbf24", "bg": "rgba(251,191,36,0.10)"},
    "life":    {"emoji": "🌱", "name": "生活", "color": "#34d399", "bg": "rgba(52,211,153,0.10)"},
    "growth":  {"emoji": "📚", "name": "成长", "color": "#fb923c", "bg": "rgba(251,146,60,0.10)"},
}
PRIORITY_META = {
    "P0": {"label": "P0 紧急", "color": "#ef4444"},
    "P1": {"label": "P1 主线", "color": "#f59e0b"},
    "P2": {"label": "P2 本周", "color": "#eab308"},
    "P3": {"label": "P3 长尾", "color": "#10b981"},
}

TODAY = date.today()
WEEKDAY_CN = ["周一","周二","周三","周四","周五","周六","周日"]


def parse_date(s):
    try:
        return datetime.strptime(s.split()[0], "%Y-%m-%d").date()
    except:
        return None


def bucket_of(task):
    if task.get("status") == "done":
        return "done"
    if task.get("status") == "cancelled":
        return "cancelled"
    
    ddl = parse_date(task.get("deadline", ""))
    if not ddl:
        return "later"
    
    if ddl < TODAY:
        return "overdue"
    elif ddl == TODAY:
        return "today"
    elif ddl == TODAY + timedelta(days=1):
        return "tomorrow"
    elif ddl <= TODAY + timedelta(days=7):
        return "thisweek"
    else:
        return "later"


# 分桶
buckets = {"overdue":[], "today":[], "tomorrow":[], "thisweek":[], "later":[], "done":[], "cancelled":[]}
for t in data["待办"]:
    b = bucket_of(t)
    if b:
        buckets[b].append(t)

# 已完成按完成日期倒序
buckets["done"].sort(key=lambda x: x.get("_completed_at", "0000"), reverse=True)

# 全部活跃任务（不含 done/cancelled）
all_active = buckets["overdue"] + buckets["today"] + buckets["tomorrow"] + buckets["thisweek"] + buckets["later"]

# 战况统计
total_active = len(all_active)
total_done = len(buckets["done"])
this_week_done = sum(1 for t in buckets["done"] 
                     if t.get("_completed_at", "") >= (TODAY - timedelta(days=7)).isoformat())


def fmt_ddl(t):
    ddl = t.get("deadline", "")
    d = parse_date(ddl)
    if not d:
        return ddl
    delta = (d - TODAY).days
    time_part = ""
    if " " in ddl:
        time_part = " " + ddl.split()[1][:5]
    if delta < 0:
        return f"⚠️ 已过期 {-delta}d"
    elif delta == 0:
        return f"今天{time_part}"
    elif delta == 1:
        return f"明天{time_part}"
    elif 0 < delta <= 7:
        return f"{d.strftime('%m/%d')} {WEEKDAY_CN[d.weekday()]}"
    else:
        return d.strftime('%Y-%m-%d')


def render_card(t, show_full=True):
    domain = DOMAIN_META.get(t.get("domain", ""), DOMAIN_META["work"])
    prio = PRIORITY_META.get(t.get("priority", "P2"), PRIORITY_META["P2"])
    is_done = t.get("status") == "done"
    is_doing = t.get("status") == "doing"
    is_cancel = t.get("status") == "cancelled"
    
    # 子任务
    sub_html = ""
    if t.get("sub_tasks"):
        items = []
        done_n = 0
        for s in t["sub_tasks"]:
            cls = "done" if s.get("done") else ""
            if s.get("done"): done_n += 1
            items.append(f'<li class="{cls}">{s["title"]}</li>')
        sub_html = f'''
        <div class="sub-progress">📋 {done_n}/{len(t["sub_tasks"])} 子任务</div>
        <ul class="subtasks">{"".join(items)}</ul>'''

    # 减重特殊渲染
    extra_html = ""
    if t.get("plan") and "目标体重曲线" in t.get("plan", {}):
        plan = t["plan"]
        log = t.get("weight_log", [])
        start, target = 166, 150
        cur = log[-1]["weight_jin"] if log else start
        prog = max(0, min(100, (start - cur) / (start - target) * 100))
        extra_html = f'''
        <div class="weight-box">
          <div class="weight-row"><span>起 {start}</span><span class="cur">现 {cur}</span><span>目标 {target}</span></div>
          <div class="weight-bar"><div class="weight-fill" style="width:{prog:.0f}%"></div></div>
        </div>'''
    
    # 训练计划渲染（T007 用）
    if t.get("training_plan_weekly"):
        twp = t["training_plan_weekly"]
        rows = []
        for s in twp.get(list(k for k in twp if k.startswith("本周"))[0] if any(k.startswith("本周") for k in twp) else "本周", []):
            mark = "✅" if s.get("完成") else "⬜"
            rows.append(f'<div class="train-row">{mark} {s.get("周几","")} {s.get("时段","")} · {s.get("类型","")} {s.get("时长_min","")}min</div>')
        if rows:
            extra_html += f'<div class="train-box"><div class="train-title">📅 本周训练计划</div>{"".join(rows)}</div>'

    # 备注（完整显示，不折叠）
    notes_html = ""
    if t.get("notes"):
        notes_html = f'<div class="notes">💬 {t["notes"]}</div>'
    
    # 完成信息
    done_block = ""
    if is_done:
        completed_at = t.get("_completed_at", "")
        memo = t.get("_完成备注", "")
        done_block = f'''<div class="done-block">
            <span class="done-tag">✅ 已完成</span>
            {f'<span class="done-date">{completed_at}</span>' if completed_at else ''}
            {f'<div class="done-memo">{memo}</div>' if memo else ''}
        </div>'''
    
    # 标签
    tags_html = ""
    if t.get("tags"):
        tags_html = '<div class="tags">' + "".join(f'<span class="tag">#{tag}</span>' for tag in t["tags"]) + '</div>'
    
    # 状态标识
    status_badge = ""
    if is_doing:
        status_badge = '<span class="status-badge doing">🟡 进行中</span>'
    elif is_done:
        status_badge = '<span class="status-badge done">✅ 已完成</span>'
    elif is_cancel:
        status_badge = '<span class="status-badge cancel">✖ 已取消</span>'
    else:
        status_badge = '<span class="status-badge todo">⬜ 待办</span>'

    done_cls = " card-done" if is_done else (" card-cancel" if is_cancel else "")
    
    action_html = ""
    if not is_done and not is_cancel and t.get("next_action_5min"):
        action_html = f'<div class="action"><span class="bolt">⚡</span><span>{t["next_action_5min"]}</span></div>'
    
    return f'''
<div class="card{done_cls}" style="--accent:{domain['color']};--accent-bg:{domain['bg']}">
  <div class="card-head">
    <span class="prio" style="background:{prio['color']}22;color:{prio['color']}">{t.get('priority','')}</span>
    <span class="domain">{domain['emoji']} {domain['name']}</span>
    <span class="ddl">{fmt_ddl(t)}</span>
    {status_badge}
  </div>
  <h3 class="card-title">{t["title"]}</h3>
  {action_html}
  {sub_html}
  {extra_html}
  {notes_html}
  {tags_html}
  {done_block}
  <div class="card-id">#{t["id"]}</div>
</div>'''


def render_section(title, subtitle, tasks, icon="", default_open=True, color="#9ca3af"):
    if not tasks:
        return ""
    cards = "\n".join(render_card(t) for t in tasks)
    open_attr = " open" if default_open else ""
    return f'''
<details class="section"{open_attr}>
  <summary class="section-head">
    <span class="section-icon">{icon}</span>
    <span class="section-title" style="color:{color}">{title}</span>
    <span class="section-count" style="background:{color}22;color:{color}">{len(tasks)}</span>
    <span class="section-sub">{subtitle}</span>
    <span class="section-arrow">▾</span>
  </summary>
  <div class="section-body">{cards}</div>
</details>'''


# ========== 各视图 ==========
view_today_html = ""
view_today_html += render_section("⚠️ 已过期", "需要立刻处理", buckets["overdue"], "🔴", True, "#ef4444")
view_today_html += render_section("今天必动", "今日核心", buckets["today"], "🎯", True, "#ef4444")
view_today_html += render_section("明天预备", "明日待动", buckets["tomorrow"], "📅", True, "#f59e0b")
view_today_html += render_section("本周内", "未来 7 天", buckets["thisweek"], "📆", True, "#fbbf24")
view_today_html += render_section("长期 / 持续", "节奏推进", buckets["later"], "🗄️", True, "#10b981")

view_active_html = ""
for t in all_active:
    view_active_html += render_card(t)

view_done_html = ""
for t in buckets["done"]:
    view_done_html += render_card(t)
if buckets["cancelled"]:
    view_done_html += '<h3 style="margin-top:32px;font-size:13px;color:#6b7280;letter-spacing:1px">✖ 已取消（合并/重组）</h3>'
    for t in buckets["cancelled"]:
        view_done_html += render_card(t)

view_all_html = ""
view_all_html += '<h3 class="all-h">活跃任务（按时间排序）</h3>'
for t in sorted(all_active, key=lambda x: x.get("deadline", "9999")):
    view_all_html += render_card(t)
view_all_html += '<h3 class="all-h" style="margin-top:32px">已完成（最近的在前）</h3>'
for t in buckets["done"]:
    view_all_html += render_card(t)


now = datetime.now().strftime("%H:%M")
date_str = TODAY.strftime("%Y-%m-%d")
weekday = WEEKDAY_CN[TODAY.weekday()]


CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0a0c10; --card:#13161d; --card2:#1a1f2a;
  --border:#222632; --border2:#2a3140;
  --text:#e8eaed; --text2:#9ca3af; --text3:#6b7280;
  --blue:#60a5fa; --green:#34d399; --red:#f87171;
}
body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","SF Pro Text","Helvetica Neue",sans-serif;
     background:var(--bg);color:var(--text);line-height:1.5;
     padding:24px 24px 80px;max-width:920px;margin:0 auto;-webkit-font-smoothing:antialiased;}
.header{margin-bottom:20px;}
.header .date{font-size:12px;color:var(--text3);letter-spacing:0.5px;}
.header h1{font-size:24px;font-weight:600;margin-top:4px;letter-spacing:-0.3px;}

/* 战况栏 */
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:20px;}
.stat-box{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:12px 14px;}
.stat-box .v{font-size:20px;font-weight:700;}
.stat-box .l{font-size:11px;color:var(--text3);margin-top:2px;}
.stat-box.overdue .v{color:var(--red);}
.stat-box.today .v{color:#fbbf24;}
.stat-box.thisweek .v{color:var(--blue);}
.stat-box.done .v{color:var(--green);}

/* 视图切换 */
.tabs{display:flex;gap:4px;margin-bottom:20px;background:var(--card2);padding:4px;border-radius:10px;width:fit-content;}
.tab{padding:8px 16px;font-size:13px;color:var(--text2);cursor:pointer;border-radius:6px;transition:all 0.15s;border:none;background:transparent;font-family:inherit;}
.tab:hover{color:var(--text);}
.tab.active{background:var(--card);color:var(--text);font-weight:600;box-shadow:0 1px 2px rgba(0,0,0,0.2);}
.view{display:none;}
.view.active{display:block;}

/* 区块 */
.section{margin-bottom:8px;border-radius:10px;}
.section-head{display:flex;align-items:center;gap:10px;padding:14px 4px 10px;cursor:pointer;list-style:none;user-select:none;}
.section-head::-webkit-details-marker{display:none;}
.section-icon{font-size:14px;}
.section-title{font-size:12px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;}
.section-count{font-size:11px;font-weight:700;padding:2px 8px;border-radius:10px;}
.section-sub{font-size:11px;color:var(--text3);margin-left:auto;}
.section-arrow{font-size:10px;color:var(--text3);transition:transform 0.2s;}
.section[open] .section-arrow{transform:rotate(180deg);}

/* 卡片 */
.card{background:var(--card);border:1px solid var(--border);border-left:3px solid var(--accent);
      border-radius:10px;padding:14px 16px;margin-bottom:8px;position:relative;}
.card:hover{border-color:var(--border2);}
.card.card-done{opacity:0.6;border-left-color:#3a4150;}
.card.card-done .card-title{text-decoration:line-through;color:var(--text2);}
.card.card-cancel{opacity:0.4;}
.card.card-cancel .card-title{text-decoration:line-through;}

.card-head{display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap;font-size:11px;}
.prio{font-weight:700;padding:2px 7px;border-radius:4px;letter-spacing:0.3px;}
.domain{color:var(--text2);}
.ddl{color:var(--text3);background:var(--card2);padding:2px 8px;border-radius:5px;font-variant-numeric:tabular-nums;margin-left:auto;}
.status-badge{padding:2px 7px;border-radius:5px;font-size:10px;}
.status-badge.todo{background:rgba(96,165,250,0.15);color:var(--blue);}
.status-badge.doing{background:rgba(251,191,36,0.15);color:#fbbf24;}
.status-badge.done{background:rgba(52,211,153,0.15);color:var(--green);}
.status-badge.cancel{background:#3a4150;color:var(--text3);}

.card-title{font-size:15px;font-weight:600;letter-spacing:-0.1px;margin-bottom:8px;}

.action{font-size:13px;color:#cbd5e1;line-height:1.55;background:var(--accent-bg);
        padding:8px 12px;border-radius:6px;margin-top:8px;display:flex;gap:8px;align-items:flex-start;}
.action .bolt{color:var(--accent);flex-shrink:0;}

.sub-progress{font-size:11px;color:var(--text3);margin-top:10px;}
.subtasks{margin-top:6px;font-size:13px;color:var(--text2);}
.subtasks li{list-style:none;padding:3px 0 3px 22px;position:relative;}
.subtasks li::before{content:"○";position:absolute;left:6px;color:var(--text3);}
.subtasks li.done::before{content:"●";color:var(--accent);}
.subtasks li.done{text-decoration:line-through;color:var(--text3);}

.weight-box{margin-top:10px;padding:10px 12px;background:var(--card2);border-radius:6px;}
.weight-row{display:flex;justify-content:space-between;font-size:12px;margin-bottom:6px;color:var(--text2);}
.weight-row .cur{color:var(--blue);font-weight:600;}
.weight-bar{height:6px;background:var(--border2);border-radius:3px;overflow:hidden;}
.weight-fill{height:100%;background:linear-gradient(90deg,#34d399,#60a5fa);}

.train-box{margin-top:10px;padding:10px 12px;background:var(--card2);border-radius:6px;}
.train-title{font-size:11px;color:var(--text3);margin-bottom:6px;letter-spacing:0.5px;}
.train-row{font-size:13px;padding:3px 0;color:var(--text2);}

.notes{font-size:12px;color:var(--text2);margin-top:10px;line-height:1.6;
       padding:8px 10px;background:rgba(255,255,255,0.02);border-radius:6px;border-left:2px solid var(--border2);}

.tags{margin-top:8px;display:flex;flex-wrap:wrap;gap:4px;}
.tag{font-size:10px;color:var(--text3);background:var(--card2);padding:2px 6px;border-radius:4px;}

.done-block{margin-top:10px;padding:8px 10px;background:rgba(52,211,153,0.08);border-radius:6px;border-left:2px solid var(--green);}
.done-tag{font-size:11px;color:var(--green);font-weight:600;}
.done-date{font-size:11px;color:var(--text3);margin-left:8px;}
.done-memo{font-size:12px;color:var(--text2);margin-top:4px;}

.card-id{position:absolute;top:8px;right:8px;font-size:9px;color:var(--text3);font-family:ui-monospace,monospace;opacity:0.5;}
.all-h{font-size:13px;color:var(--text3);letter-spacing:1px;margin-bottom:12px;text-transform:uppercase;}

.footer{margin-top:48px;padding-top:20px;border-top:1px solid var(--border);
        font-size:12px;color:var(--text3);text-align:center;line-height:1.7;}
.footer code{background:var(--card2);padding:2px 6px;border-radius:4px;color:var(--blue);}

@media (max-width:700px){
  body{padding:16px 12px 60px;}
  .stats{grid-template-columns:repeat(2,1fr);}
  .header h1{font-size:20px;}
}
"""

JS = """
function switchView(name){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));
  document.querySelector('.tab[data-view="'+name+'"]').classList.add('active');
  document.getElementById('view-'+name).classList.add('active');
}
"""

html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>待办看板 · 工作助手</title>
<style>{CSS}</style>
</head>
<body>

<div class="header">
  <div class="date">{date_str} · {weekday} · 更新于 {now}</div>
  <h1>📋 工作助手 · 待办看板</h1>
</div>

<div class="stats">
  <div class="stat-box overdue"><div class="v">{len(buckets['overdue'])}</div><div class="l">⚠️ 已过期</div></div>
  <div class="stat-box today"><div class="v">{len(buckets['today'])}</div><div class="l">🎯 今天必动</div></div>
  <div class="stat-box thisweek"><div class="v">{len(buckets['tomorrow']) + len(buckets['thisweek'])}</div><div class="l">📆 本周内</div></div>
  <div class="stat-box done"><div class="v">{this_week_done}</div><div class="l">✅ 7 天内完成</div></div>
</div>

<div class="tabs">
  <button class="tab active" data-view="today" onclick="switchView('today')">📅 时间分桶</button>
  <button class="tab" data-view="active" onclick="switchView('active')">⏳ 仅待办（{total_active}）</button>
  <button class="tab" data-view="done" onclick="switchView('done')">✅ 已完成（{total_done}）</button>
  <button class="tab" data-view="all" onclick="switchView('all')">📊 全部</button>
</div>

<div id="view-today" class="view active">
  {view_today_html}
</div>

<div id="view-active" class="view">
  {view_active_html}
</div>

<div id="view-done" class="view">
  {view_done_html}
</div>

<div id="view-all" class="view">
  {view_all_html}
</div>

<div class="footer">
  数据：<code>数据/12_待办.json</code> · 看板：<code>今日待办.html</code><br>
  共 {len(data["待办"])} 条记录（活跃 {total_active} · 已完成 {total_done} · 已取消 {len(buckets['cancelled'])}）
</div>

<script>{JS}</script>

</body>
</html>
"""

(ROOT / '今日待办.html').write_text(html, encoding='utf-8')
print(f"✅ 看板已重建（v3）")
print(f"  活跃 {total_active} | 已完成 {total_done} | 7 天完成 {this_week_done}")
print(f"  4 个视图：时间分桶 / 仅待办 / 已完成 / 全部")
