# Work Assistant（工作助手）

对抗拖延的本地「数据固化」工作台：Mac 任务看板 + 菜单栏 + 定时通知 + 给 AI 用的分层记忆。

> 本仓库是**脱敏后的开源模板**。不含真实财务、履历、合同、聊天记录。

## 功能

- **任务看板**：Today / 全部 / 已完成，支持完成、新增、推迟、习惯打卡、子任务
- **菜单栏常驻**：瞄一眼今日聚焦数，快速完成/新增
- **定时通知**：早上/中午/下午/晚上（LaunchAgent）
- **并发安全写 JSON**：自动备份到 `数据/.history/`
- **AI 友好记忆**：`AGENTS.md` + `_记忆/` + 事件流，方便 Cursor / Claude 接手

## 快速开始（macOS）

```bash
git clone https://github.com/tom7523326/work-assistant.git
cd work-assistant
chmod +x 启动任务看板.command 启动菜单栏.command 通知_安装.command 通知_卸载.command

# 需要带 tkinter 的 Python
brew install python-tk@3.12

# 可选：菜单栏
/usr/bin/python3 -m pip install --user rumps

# 启动看板
./启动任务看板.command
```

示例待办在 `数据/12_待办.json`，直接改就能在 App 里看到。

## 目录

```
work-assistant/
├── 任务看板.py / 菜单栏.py / 通知.py / 数据备份.py
├── 启动*.command / 通知_安装.command / 通知_卸载.command
├── launchd/                 # LaunchAgent 模板（安装时写实路径）
├── 数据/                    # 示例 JSON（请换成你自己的）
├── _记忆/                   # SOUL / MEMORY / today 模板
├── AGENTS.md                # AI 接手索引
└── skills/work-life-companion/
```

## 隐私

开源包刻意去掉了：

- 真实姓名、公司内部项目、银行卡/合同号
- 工资、贷款、持仓、信用卡账单
- 简历/绩效截图、家庭健康记录
- 本地原始材料目录（财务/工作/投资等）

请勿把私有 `数据/` 覆盖回公开仓库。

## License

MIT
