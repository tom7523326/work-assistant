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
