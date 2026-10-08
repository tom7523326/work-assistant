# AGENTS.md — AI 入口索引（开源模板）

> 任何 AI 接手这个工作区时，先读本文件。

## 必读顺序

```
1. AGENTS.md（本文件）
2. _记忆/SOUL.md
3. 数据/_事件流.jsonl（tail -30）
4. _记忆/today.md
5. _记忆/MEMORY.md（按需）
6. 数据/12_待办.json（回答待办问题时）
```

## Skill 统一入口

本工作区的技能统一放在 [skills/](skills/README.md)。遇到口播稿、整期课程制作、待办协作或技能创建任务，先读 [技能目录](skills/README.md) 或 [机器可读索引](skills/skills.json)，再进入匹配的 SKILL.md。

| Skill | 什么时候用 |
|---|---|
| [shouge-spoken-script](skills/shouge-spoken-script/SKILL.md) | 写、改、精简课程口播 |
| [shouge-course-production](skills/shouge-course-production/SKILL.md) | 按一套固定流程做整期课程视频 |
| [work-life-companion](skills/work-life-companion/SKILL.md) | 待办、个人资料、工作/生活协作 |
| [skill-creator-prod](skills/skill-creator-prod/SKILL.md) | 创建或改进技能（第三方框架，Apache-2.0） |

跨 agent 读取不依赖特定工具的调用语法，直接按路径读文件即可。入口说明另见 [CLAUDE.md](CLAUDE.md)。

## 记忆分层

```
L3 SOUL      → _记忆/SOUL.md
L2 Skill/Mem → _记忆/MEMORY.md · _记忆/SKILL.md · skills/
L1 Atom      → 数据/*.json
L0 Raw       → 你自己的原始材料目录（本开源包不含）
```

## 核心程序

| 文件 | 用途 |
|---|---|
| `任务看板.py` | Mac 桌面任务看板（Today / 全部 / 已完成） |
| `菜单栏.py` | 顶部状态栏今日聚焦数 |
| `数据备份.py` | `safe_load` / `safe_save` / `atomic_update` |
| `通知.py` + `launchd/` | 定时提醒 + 菜单栏自启 |
| `启动任务看板.command` | 双击启动（推荐） |
| `build_todo.py` | 生成网页看板 `今日待办.html`（工作/生活/财务分区筛选） |
| `examples/day13-starter-pack/` | 课程配套示例：起点/终点页面 + 样例 CSV + 跟做提示词 |

## 给接手 AI 的硬约束

1. 开场不要说「我注意到这是新对话」
2. 拖延症友好：短句、列点、最多 1-2 个问题
3. 改 `12_待办.json` 后：同步 `_today_focus`、写 `_事件流.jsonl`、校验 JSON
4. **不要把真实隐私数据提交到公开仓库**

## 运维

- 启动：双击 `启动任务看板.command`
- 菜单栏：双击 `启动菜单栏.command`
- 安装通知：双击 `通知_安装.command`（会把 `__WORK_ASSISTANT_ROOT__` 改写成当前路径）
- Python：需带 tkinter（`brew install python-tk@3.12`）
- 可选：`pip3 install rumps`（菜单栏）

**开源包数据基准日**：2026-09-30（示例数据）
