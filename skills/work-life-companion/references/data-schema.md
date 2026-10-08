# Data Schema（数据底座结构速查）

工作助手项目的所有 JSON 数据定义。修改前先读这里。

## 13 个 JSON 文件总览

| 文件 | 内容 | 是否可写 |
|---|---|---|
| `00_汇总.json` | 财务汇总（资产/负债/现金流/关键比率）| 🟡 用户主导更新 |
| `01_收入.json` | 工资/股权/公积金/租金等收入 | 🟡 |
| `02_贷款.json` | 贷款明细 + 关键节点 | 🟡 |
| `03_信用卡.json` | 5 张信用卡 + 提醒事项 | 🟡 |
| `04_投资.json` | 雪球持仓 | 🟡 |
| `05_日常花费.json` | 月度消费明细 | 🟡 |
| `06_车辆.json` | 车辆信息 | 🟡 |
| `07_保险.json` | 重疾险 + 车险 | 🟡 |
| `08_岗位与履历.json` | 简历 + 历次绩效 | 🟡 |
| `09_工作目标.json` | 历史 OKR | 🟡 |
| `10_项目清单.json` | 在做项目 | 🟡 |
| `11_职业规划.json` | 短/中/长期 | 🟡 |
| `12_待办.json` | **AI 高频读写** | ✅ |
| `14_人脉.json` | 联系人档案 | ✅ |

## 12_待办.json 关键字段

```json
{
  "id": "T0NN",                    // 唯一 ID，递增
  "title": "任务标题（可带 emoji）",
  "domain": "family|work|finance|life|growth",
  "priority": "P0|P1|P2|P3",
  "status": "todo|doing|done|blocked|cancelled",
  "created": "YYYY-MM-DD",
  "deadline": "YYYY-MM-DD HH:MM",   // 时分可选
  "event_date": "YYYY-MM-DD",        // 实际事件发生日（与 deadline 不同）
  "next_action_5min": "5 分钟内能动的具体动作",
  "notes": "详情/备注",
  "tags": ["..."],
  "sub_tasks": [
    {"title": "...", "done": false}
  ],
  "_completed_at": "YYYY-MM-DD",     // status=done 时填
  "_完成备注": "完成时的具体记录",
  "_合并到": "T0NN",                 // status=cancelled 因合并时填
  "_注": "状态说明"
}
```

### Domain 枚举
- `family` 家庭（紫色 #a78bfa）
- `work` 工作（蓝色 #60a5fa）
- `finance` 财务（金色 #d4af37）
- `life` 生活（绿色 #34d399）
- `growth` 成长（橙色 #fb923c）

### Priority 枚举
- `P0` 红色 #ff5d5d - 当日紧急
- `P1` 橙色 #ffa45d - 本周主线
- `P2` 黄色 #ffd95d - 本周内
- `P3` 绿色 #7dd3a8 - 长尾

## 14_人脉.json 关键字段

```json
{
  "id": "C0NN",
  "姓名": "...",
  "电话": "...",                    // 完整存储，看板侧手机号脱敏显示
  "微信": "...",
  "邮箱": "...",
  "关系": "前同事/前下属/前上级/客户/朋友",
  "关系强度": "high|medium|low",     // 🟢🟡🔴
  "现公司_现职位": "...",
  "履历": "...",
  "行业定位": "...",
  "战略价值": 1-5,                  // 1-5 颗星
  "战略价值理由": "...",
  "上次见面": "YYYY-MM-DD 描述",
  "下次见面计划": "YYYY-MM-DD HH:MM 类型",
  "需补充": ["..."],
  "你欠对方": "...",
  "对方欠你": "..."
}
```

## 00_汇总.json 高频读取字段

```python
# 净资产
huizong["资产负债表_快照"]["净资产"]

# 月度净储蓄（非奖金月）
huizong["现金流_月"]["净储蓄能力_月_非奖金"]    # 注意字段名：不是"月度净储蓄"

# 紧急储备金覆盖月数
huizong["关键比率_预警"]["紧急储备金覆盖_月"]

# 本月重要事项（财务节点）
for ev in huizong["本月_5月_重要事项"]:
    print(ev["日期"], ev["事项"], ev.get("金额"))
```

## 贷款文件高频读取字段

```python
# 关键节点
for ev in daikuan["_重要节点提醒"]:
    print(ev["日期"], ev["事项"], ev.get("金额"))
```

## SOUL.md 关键章节

| Section | 内容 | 修改阈值 |
|---|---|---|
| 1. 身份卡 | 年龄/职级/家庭基础信息 | 极少改 |
| 2. 用户偏好 | 沟通风格/工作节奏 | 用户明确反馈才改 |
| 3. 边界（不能做的事）| 强约束清单 | 添加新约束 |
| 4. 三个非显而易见洞察 | 深层理解 | 重大认知变化才改 |
| 4.5. 已有工程弹药 | 真实能力档位 | 新项目落地才改 |
| 5. 长期目标 | 短/中/长期方向 | 战略级变化才改 |
| 6. 默认回复风格 | 短句、emoji 节制等 | 几乎不改 |

## MEMORY.md 用法

存"硬事实"，**不存**用户画像（那是 SOUL）也不存协作 SOP（那是项目内 SKILL.md，不是本 skill）。

例：
- 妻子生日 = 5/14
- 孩子生日 = MM/DD
- 孩子学校：xxx
- 家庭住址：xxx
- 重要项目代号：xxx

## 看板渲染脚本

| 脚本 | 输出 | 用法 |
|---|---|---|
| `build_todo.py` | `今日待办.html` | 数据更新后必跑 |
| `build_contacts.py` | `人脉档案.html` | 14_人脉.json 更新后跑 |

**双刷常规命令**：
```bash
cd "$WORK_ASSISTANT_ROOT" && python3 build_todo.py
```

## ID 分配规则

```python
# 12_待办.json
existing = [int(t["id"][1:]) for t in d["待办"] if t["id"].startswith("T")]
next_id = max(existing) + 1
new_id = f"T{next_id:03d}"

# 14_人脉.json
# 同模式，前缀是 C
```
