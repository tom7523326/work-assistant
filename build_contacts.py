"""
人脉档案看板构建器
设计原则：
  1. 4 个视图：联系人列表 / 该联系了 / 即将见面 / 互动时间轴
  2. 关系强度色编码（🟢🟡🔴）
  3. 电话默认部分隐藏，悬停显示
  4. 战略价值用星标
  5. 见面前 5 分钟必看的"互动时间轴"
"""
import json
from pathlib import Path
from datetime import datetime, date, timedelta
import re

ROOT = Path(__file__).resolve().parent
data = json.loads((ROOT / '数据' / '14_人脉.json').read_text(encoding='utf-8'))

TODAY = date.today()
WEEKDAY_CN = ["周一","周二","周三","周四","周五","周六","周日"]

contacts = data.get("联系人", [])
interactions = data.get("互动记录", [])

# 按联系人聚合互动
inter_by_p = {}
for i in interactions:
    pid = i.get("联系人id", "")
    inter_by_p.setdefault(pid, []).append(i)

# 解析"上次见面"字段，估算距今多久（粗略）
def days_since(s):
    """支持 '2022-05-15' / '2022 年左右' / '2022（约）' 等格式"""
    if not s:
        return None
    m = re.search(r'(\d{4})(?:[-年](\d{1,2})(?:[-月](\d{1,2}))?)?', s)
    if not m:
        return None
    y = int(m.group(1))
    mo = int(m.group(2)) if m.group(2) else 6  # 没月份，按年中估
    day = int(m.group(3)) if m.group(3) else 15
    try:
        d = date(y, mo, day)
        return (TODAY - d).days
    except:
        return None


def relation_color(level):
    return {"🟢": "#34d399", "🟡": "#fbbf24", "🔴": "#f87171"}.get(level, "#6b7280")


def fmt_phone(p):
    """中间 4 位脱敏，data-full 给悬停展开"""
    if not p:
        return ""
    if len(p) >= 7:
        masked = p[:3] + "****" + p[-4:]
        return f'<span class="phone" data-full="{p}" title="点击复制">{masked}</span>'
    return p


def render_contact_card(c, show_full_history=False):
    pid = c["id"]
    inter_list = inter_by_p.get(pid, [])
    last_seen = c.get("上次见面", "")
    days = days_since(last_seen)
    
    # 关系强度色
    rel_color = relation_color(c.get("关系强度", ""))
    
    # 多久没见
    if days is None:
        last_text = last_seen or "—"
    elif days < 30:
        last_text = f"{days} 天前"
    elif days < 365:
        last_text = f"{days // 30} 个月前"
    else:
        years = days // 365
        last_text = f"约 {years} 年前"
    
    # 即将见面
    next_meet_html = ""
    if c.get("下次见面计划"):
        next_meet_html = f'<div class="next-meet">📅 下次：{c["下次见面计划"]}</div>'
    
    # 履历链
    bio_html = ""
    if c.get("履历"):
        bio_chain = " → ".join(c["履历"])
        bio_html = f'<div class="bio">{bio_chain}</div>'
    
    # 战略标签
    strat_html = ""
    if c.get("战略价值"):
        reason = c.get("战略价值理由", "")
        strat_html = f'<div class="strat"><span class="stars">{c["战略价值"]}</span><span class="strat-r">{reason}</span></div>'
    
    # 待补充
    todo_fill = ""
    if c.get("需补充"):
        items = "".join(f"<li>{x}</li>" for x in c["需补充"])
        todo_fill = f'<div class="fill-block"><div class="fill-title">🟡 待补充</div><ul>{items}</ul></div>'
    
    # 欠人情
    debts_html = ""
    if c.get("你欠对方") or c.get("对方欠你"):
        you_owe = c.get("你欠对方", [])
        owe_you = c.get("对方欠你", [])
        if you_owe or owe_you:
            debts_html = '<div class="debts">'
            if you_owe:
                debts_html += '<div class="debt-row"><span class="debt-tag you">你欠对方</span><span>' + " · ".join(you_owe) + '</span></div>'
            if owe_you:
                debts_html += '<div class="debt-row"><span class="debt-tag him">对方欠你</span><span>' + " · ".join(owe_you) + '</span></div>'
            debts_html += '</div>'
    
    # 互动时间轴（详情视图才完整展开）
    timeline_html = ""
    if inter_list:
        rows = []
        for i in sorted(inter_list, key=lambda x: x.get("日期", "0"), reverse=True):
            topics = " · ".join(i.get("关键话题", [])) if i.get("关键话题") else "—"
            rows.append(f'''
            <div class="ti-row">
              <div class="ti-date">{i.get("日期", "—")}</div>
              <div class="ti-body">
                <div class="ti-form">{i.get("形式", "")}<span class="ti-loc">{" · " + i["地点"] if i.get("地点") else ""}</span></div>
                <div class="ti-topics">💬 {topics}</div>
                {f'<div class="ti-mood">🌤 {i["情绪/氛围"]}</div>' if i.get("情绪/氛围") else ""}
                {f'<div class="ti-memo">{i["复盘备注"]}</div>' if i.get("复盘备注") else ""}
              </div>
            </div>''')
        timeline_html = f'<div class="timeline">{"".join(rows)}</div>'
    
    contacts_block = ""
    if c.get("电话") or c.get("微信") or c.get("邮箱"):
        items = []
        if c.get("电话"): items.append(f'📱 {fmt_phone(c["电话"])}')
        if c.get("微信"): items.append(f'💬 {c["微信"]}')
        if c.get("邮箱"): items.append(f'✉️ {c["邮箱"]}')
        contacts_block = f'<div class="contacts">{" · ".join(items)}</div>'
    
    return f'''
<div class="pcard" style="--rel:{rel_color}">
  <div class="pcard-head">
    <div class="pcard-name">
      <span class="rel-dot">{c.get("关系强度", "")}</span>
      <span class="name">{c.get("姓名", "")}</span>
      <span class="rel-text">{c.get("关系", "")}</span>
    </div>
    <div class="last-seen">上次：{last_text}</div>
  </div>
  
  <div class="pcard-pos">{c.get("现公司_现职位", "")}</div>
  {f'<div class="industry">🎯 {c["行业定位"]}</div>' if c.get("行业定位") else ""}
  {bio_html}
  {strat_html}
  {contacts_block}
  {next_meet_html}
  {todo_fill}
  {debts_html}
  
  <details class="timeline-fold">
    <summary>📜 互动时间轴（{len(inter_list)} 条）</summary>
    {timeline_html if timeline_html else '<div class="empty">暂无互动记录</div>'}
  </details>
</div>'''


# ========== 构建各视图 ==========

# 视图 1：联系人列表（按战略价值 + 关系强度排序）
def sort_key(c):
    star_count = c.get("战略价值", "").count("⭐")
    rel_score = {"🟢": 3, "🟡": 2, "🔴": 1}.get(c.get("关系强度",""), 0)
    return (-star_count, -rel_score)

view_list_html = ""
for c in sorted(contacts, key=sort_key):
    view_list_html += render_contact_card(c)

# 视图 2：该联系了（≥3 个月没见）
need_reach_out = [c for c in contacts if (days_since(c.get("上次见面","")) or 0) >= 90]
view_reach_html = ""
if need_reach_out:
    for c in need_reach_out:
        view_reach_html += render_contact_card(c)
else:
    view_reach_html = '<div class="empty-section">🎉 没有需要紧急联系的人</div>'

# 视图 3：即将见面
upcoming = [c for c in contacts if c.get("下次见面计划")]
view_upcoming_html = ""
if upcoming:
    for c in upcoming:
        view_upcoming_html += render_contact_card(c)
else:
    view_upcoming_html = '<div class="empty-section">没有已排期的见面</div>'


total_contacts = len(contacts)
total_inter = len(interactions)
need_reach_count = len(need_reach_out)
upcoming_count = len(upcoming)
green_count = sum(1 for c in contacts if c.get("关系强度") == "🟢")

now = datetime.now().strftime("%H:%M")
date_str = TODAY.strftime("%Y-%m-%d")
weekday = WEEKDAY_CN[TODAY.weekday()]


CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0a0c10; --card:#13161d; --card2:#1a1f2a;
  --border:#222632; --border2:#2a3140;
  --text:#e8eaed; --text2:#9ca3af; --text3:#6b7280;
  --blue:#60a5fa; --green:#34d399; --red:#f87171; --yellow:#fbbf24; --purple:#a78bfa;
}
body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","SF Pro Text","Helvetica Neue",sans-serif;
     background:var(--bg);color:var(--text);line-height:1.55;
     padding:24px 24px 80px;max-width:920px;margin:0 auto;-webkit-font-smoothing:antialiased;}

.header{margin-bottom:20px;}
.header .date{font-size:12px;color:var(--text3);letter-spacing:0.5px;}
.header h1{font-size:24px;font-weight:600;margin-top:4px;letter-spacing:-0.3px;}
.header .sub{font-size:13px;color:var(--text2);margin-top:6px;}

.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:20px;}
.stat-box{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:12px 14px;}
.stat-box .v{font-size:22px;font-weight:700;}
.stat-box .l{font-size:11px;color:var(--text3);margin-top:2px;}
.stat-box.total .v{color:var(--blue);}
.stat-box.green .v{color:var(--green);}
.stat-box.reach .v{color:var(--yellow);}
.stat-box.upcoming .v{color:var(--purple);}

.tabs{display:flex;gap:4px;margin-bottom:20px;background:var(--card2);padding:4px;border-radius:10px;width:fit-content;flex-wrap:wrap;}
.tab{padding:8px 14px;font-size:13px;color:var(--text2);cursor:pointer;border-radius:6px;
     transition:all 0.15s;border:none;background:transparent;font-family:inherit;}
.tab:hover{color:var(--text);}
.tab.active{background:var(--card);color:var(--text);font-weight:600;box-shadow:0 1px 2px rgba(0,0,0,0.2);}
.view{display:none;}
.view.active{display:block;}

.pcard{background:var(--card);border:1px solid var(--border);border-left:3px solid var(--rel);
       border-radius:10px;padding:16px 18px;margin-bottom:10px;}
.pcard:hover{border-color:var(--border2);}

.pcard-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;flex-wrap:wrap;gap:8px;}
.pcard-name{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
.rel-dot{font-size:14px;}
.name{font-size:18px;font-weight:600;letter-spacing:-0.2px;}
.rel-text{font-size:12px;color:var(--text2);background:var(--card2);padding:2px 8px;border-radius:5px;}
.last-seen{font-size:12px;color:var(--text3);}

.pcard-pos{font-size:14px;color:var(--text2);margin-bottom:6px;}
.industry{font-size:13px;color:var(--text2);margin-bottom:8px;}
.bio{font-size:12px;color:var(--text3);margin-bottom:10px;font-style:italic;}

.strat{margin:10px 0;padding:8px 10px;background:rgba(167,139,250,0.08);border-radius:6px;border-left:2px solid var(--purple);}
.stars{font-size:14px;}
.strat-r{font-size:12px;color:var(--text2);margin-left:8px;display:block;margin-top:4px;}

.contacts{margin:8px 0;font-size:13px;color:var(--text2);}
.phone{cursor:pointer;border-bottom:1px dashed var(--text3);font-variant-numeric:tabular-nums;}
.phone:hover{color:var(--blue);}

.next-meet{margin:10px 0;padding:8px 10px;background:rgba(96,165,250,0.10);border-radius:6px;
           font-size:13px;color:var(--blue);font-weight:500;border-left:2px solid var(--blue);}

.fill-block{margin:10px 0;padding:8px 10px;background:rgba(251,191,36,0.06);border-radius:6px;border-left:2px solid var(--yellow);}
.fill-title{font-size:11px;color:var(--yellow);margin-bottom:4px;font-weight:600;}
.fill-block ul{padding-left:18px;font-size:12px;color:var(--text2);}

.debts{margin:10px 0;}
.debt-row{font-size:12px;color:var(--text2);padding:4px 0;display:flex;gap:8px;align-items:center;}
.debt-tag{font-size:10px;padding:2px 6px;border-radius:3px;font-weight:600;}
.debt-tag.you{background:rgba(248,113,113,0.15);color:var(--red);}
.debt-tag.him{background:rgba(52,211,153,0.15);color:var(--green);}

.timeline-fold{margin-top:12px;padding-top:10px;border-top:1px solid var(--border);}
.timeline-fold summary{font-size:12px;color:var(--text3);cursor:pointer;padding:4px 0;}
.timeline-fold summary:hover{color:var(--text2);}
.timeline-fold[open] summary{margin-bottom:8px;}

.timeline{padding-left:8px;border-left:2px solid var(--border2);margin-left:4px;}
.ti-row{padding:8px 0 8px 16px;position:relative;}
.ti-row::before{content:"";position:absolute;left:-7px;top:14px;width:8px;height:8px;border-radius:50%;background:var(--text3);}
.ti-date{font-size:11px;color:var(--text3);font-variant-numeric:tabular-nums;margin-bottom:4px;}
.ti-form{font-size:13px;color:var(--text);font-weight:500;}
.ti-loc{color:var(--text3);font-weight:400;}
.ti-topics{font-size:12px;color:var(--text2);margin-top:4px;}
.ti-mood{font-size:12px;color:var(--text3);margin-top:2px;}
.ti-memo{font-size:11px;color:var(--text3);margin-top:4px;font-style:italic;}

.empty{font-size:12px;color:var(--text3);text-align:center;padding:12px;}
.empty-section{padding:48px;text-align:center;color:var(--text3);font-size:14px;}

.footer{margin-top:48px;padding-top:20px;border-top:1px solid var(--border);
        font-size:12px;color:var(--text3);text-align:center;line-height:1.7;}
.footer code{background:var(--card2);padding:2px 6px;border-radius:4px;color:var(--blue);}
.footer .priv{color:var(--yellow);}

@media (max-width:700px){
  body{padding:16px 12px 60px;}
  .stats{grid-template-columns:repeat(2,1fr);}
}
"""

JS = """
function switchView(name){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));
  document.querySelector('.tab[data-view="'+name+'"]').classList.add('active');
  document.getElementById('view-'+name).classList.add('active');
}
// 电话点击复制完整号码
document.addEventListener('click', e => {
  if (e.target.classList.contains('phone')) {
    const full = e.target.dataset.full;
    if (full) {
      navigator.clipboard.writeText(full).then(()=>{
        const orig = e.target.textContent;
        e.target.textContent = '✓ 已复制 '+full;
        setTimeout(()=>{e.target.textContent=orig;}, 1500);
      });
    }
  }
});
"""


html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>人脉档案 · 工作助手</title>
<style>{CSS}</style>
</head>
<body>

<div class="header">
  <div class="date">{date_str} · {weekday} · 更新于 {now}</div>
  <h1>📇 人脉档案</h1>
  <div class="sub">长期关系经营 · 见面前 5 分钟必看</div>
</div>

<div class="stats">
  <div class="stat-box total"><div class="v">{total_contacts}</div><div class="l">📇 联系人</div></div>
  <div class="stat-box green"><div class="v">{green_count}</div><div class="l">🟢 强关系</div></div>
  <div class="stat-box reach"><div class="v">{need_reach_count}</div><div class="l">🔥 该联系了</div></div>
  <div class="stat-box upcoming"><div class="v">{upcoming_count}</div><div class="l">📅 即将见面</div></div>
</div>

<div class="tabs">
  <button class="tab active" data-view="list" onclick="switchView('list')">📇 联系人（{total_contacts}）</button>
  <button class="tab" data-view="upcoming" onclick="switchView('upcoming')">📅 即将见面（{upcoming_count}）</button>
  <button class="tab" data-view="reach" onclick="switchView('reach')">🔥 该联系了（{need_reach_count}）</button>
</div>

<div id="view-list" class="view active">
  {view_list_html}
</div>

<div id="view-upcoming" class="view">
  {view_upcoming_html}
</div>

<div id="view-reach" class="view">
  {view_reach_html}
</div>

<div class="footer">
  数据：<code>数据/14_人脉.json</code> · 共 {total_contacts} 位联系人 / {total_inter} 条互动记录<br>
  <span class="priv">⚠️ 含敏感信息（手机号等）。如需同步代码仓，必须 .gitignore 此文件。</span>
</div>

<script>{JS}</script>

</body>
</html>
"""

(ROOT / '人脉档案.html').write_text(html, encoding='utf-8')
print(f"✅ 人脉档案看板已生成")
print(f"  联系人 {total_contacts} | 互动记录 {total_inter}")
print(f"  即将见面 {upcoming_count} | 该联系了 {need_reach_count}")
