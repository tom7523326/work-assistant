# Task Add Pattern（入库新事项的标准 SOP）

最高频操作。任何"记一下/入库 X"的请求都走这套。

## 标准流程（5 步）

### Step 1: 确定 ID

```python
import json
from pathlib import Path

p = Path('数据/12_待办.json')  # 相对工作区根目录运行
d = json.loads(p.read_text(encoding='utf-8'))

existing = [int(t["id"][1:]) for t in d["待办"] if t["id"].startswith("T")]
next_id = max(existing) + 1
new_id = f"T{next_id:03d}"
```

### Step 2: 决定字段值

#### Domain 判断

| 关键词 | Domain |
|---|---|
| 孩子 / 媳妇 / 父母 / 家里 / 露营 / 生日 | `family` |
| 项目 / 合同 / 汇报 / 客户 / OA / 上级 | `work` |
| 还款 / 信用卡 / 退税 / 报销 / 余额 | `finance` |
| 健身 / 减重 / 饮食 / 体检 / 旅行 | `life` |
| AI / 学习 / 内容 / X / 即刻 / KOL / OPC | `growth` |

#### Priority 判断

| 信号 | Priority |
|---|---|
| 今天必须做 / 不做出大事 / 已过期 | `P0` |
| 本周主线 / 关键决策 / 时间点紧迫 | `P1` |
| 本周内做 / 截止日 ≤ 7 天 | `P2` |
| 长期 / 持续 / 没有硬截止 | `P3` |

#### Deadline 推导

| 用户说法 | deadline |
|---|---|
| "今天/今晚" | `YYYY-MM-DD HH:MM`（取合理时间） |
| "明天" | 明天 22:00 |
| "本周内/这周搞定" | 本周日 22:00 |
| "下周" | 下周日 22:00 |
| "下个月" | 下月底 |
| "争取 X 月前" | 取用户提到的具体日期 |
| 没说时间 | 加 7 天 + notes 标"待澄清截止" |

#### Next Action 5min 必填

**永远具体可动作**，不要"思考一下""规划一下"这种：

| ❌ 不好 | ✅ 好 |
|---|---|
| "想想买什么" | "京东搜「书客大路灯」加入购物车" |
| "梳理一下" | "下午 14:00 找 90 分钟整块时间，从问题陈述开始" |
| "了解一下" | "周三晚让 Claude Code 读项目并提取 5 个工程坑" |

### Step 3: 写入（必须 Python + UTF-8）

```python
new_task = {
    "id": new_id,
    "title": "...",
    "domain": "...",
    "priority": "...",
    "status": "todo",
    "created": "YYYY-MM-DD",
    "deadline": "...",
    "next_action_5min": "...",
    "notes": "...",
    "tags": [...]
}

# 可选：sub_tasks（多步骤任务）
new_task["sub_tasks"] = [
    {"title": "...", "done": False},
    ...
]

d["待办"].append(new_task)
d["_最后更新"] = "YYYY-MM-DD HH:MM"
p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
```

⚠️ **绝对不能用** `echo "..." > file.json` 或任何 shell 重定向写中文 JSON。

### Step 4: 双刷看板

```bash
cd "$WORK_ASSISTANT_ROOT" && python3 build_todo.py
```

### Step 5: 简短确认

```
✅ T0NN 入库（[priority]·[deadline]）
```

**不要**:
- ❌ 长篇总结刚做了啥
- ❌ 主动建议优先级砍除
- ❌ 给 A/B/C 选项问下一步

**可以**:
- ✅ 1-2 句关键提醒（特别是发现事项之间有依赖/冲突时）
- ✅ 涉及风险的地方提一下（财务损失、医疗安全、不可逆操作）

## 多任务一次性入库

用户一次扔 3+ 件事时：

```python
new_tasks = [
    { "id": f"T{next_id:03d}", ... },
    { "id": f"T{next_id+1:03d}", ... },
    { "id": f"T{next_id+2:03d}", ... },
]

d["待办"].extend(new_tasks)
```

确认时一句话：`✅ 已入库 N 个新任务（T0NN ~ T0MM）`

## 特殊情况处理

### 信息不完整时

用户说"记一下：周三给孩子买个东西"，没说什么东西、什么时间、为什么。

**做法**：
1. 用最朴素假设入库
2. notes 字段标 `详情待补充`
3. 简短问 1 个最关键的问题（不要 3 个一起问）

### 修改已有任务

```python
for t in d["待办"]:
    if t["id"] == "T0NN":
        t["status"] = "..."
        t["..."] = "..."
```

修改记录用 `_最后更新` 字段，不要新增字段污染 schema。

### 子任务进度更新

```python
for t in d["待办"]:
    if t["id"] == "T0NN":
        for s in t["sub_tasks"]:
            if "关键词" in s["title"]:
                s["done"] = True
```

如果某个 sub_task 完成但不是全部完成，**主任务保持 doing**，不要标 done。

### 任务合并

当用户提到"X 和 Y 其实是一件事"或者你识别出强依赖时：

1. 把要被合并的任务 status 改为 `cancelled`
2. 添加 `_合并到` 字段标明去向
3. 创建一个聚合任务，把原任务作为 sub_tasks
4. 不删原任务（保留追溯）

## 错误恢复

写完跑 build 报错？通常是 JSON 损坏。立刻：

```bash
python3 -m json.tool 数据/12_待办.json > /dev/null
# 如果报错，从 git 恢复：
git checkout -- 数据/12_待办.json
```

## 真实例子参考

查 `数据/12_待办.json` 里 T020（聚合任务）/ T021（带 sub_tasks 的项目类）/ T031（高优先级 KOL 任务）作为模板参考。
