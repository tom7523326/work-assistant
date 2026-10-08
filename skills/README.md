# 工作助手 Skill 统一目录

这里是本工作区自建与导入 Skill 的统一源目录。Codex、Claude Code、Cursor 或其他能读文件的 agent 都从本页选择对应技能，再读取该目录的 SKILL.md。

## 技能目录

| Skill | 什么时候用 | 入口 |
|---|---|---|
| 寿哥口语逐字稿 | 写、续写、精简课程口播，沿用本人前12期自然口语 | [shouge-spoken-script](shouge-spoken-script/SKILL.md) |
| 寿哥课程视频制作 | 按Day13整套流程做下一课；导图、NotebookLM、口语稿、Gemini二审、真实实操、数字人、封面与发布 | [shouge-course-production](shouge-course-production/SKILL.md) |
| 工作与生活协作 | 待办、个人资料、工作/家庭/财务等跨领域协作 | [work-life-companion](work-life-companion/SKILL.md) |
| Skill Creator 导入版 | 创建/改进技能时参考的既有Manus框架 | [skill-creator-prod](skill-creator-prod/SKILL.md) |

## 给其他 agent 的使用方法

1. 先读工作区根目录 [AGENTS.md](../AGENTS.md)，按任务确认相关记忆和数据。
2. 根据上表或 [skills.json](skills.json) 找到匹配的入口，读取该 Skill 的 SKILL.md。
3. 只按该 Skill 的指引读必要 references；不一次加载全部技能或全部语料。
4. 不支持美元符号调用语法的工具，直接按路径读文件即可。
5. 只有口播稿时用口语 Skill；做整期课程时用课程制作 Skill，再由它调用口语 Skill。

在 Codex 里可把 shouge-spoken-script、shouge-course-production 安装为用户级技能（链接指向本目录）；其他 agent 直接按路径读 SKILL.md 即可。

导入版框架的frontmatter原名为skill-creator，保留原样；用skill-creator-prod目录区分它与Codex内置同名技能，不把两者当成同一实现。

## 开源版说明

- 本目录是脱敏后的公开副本：不含前12期成片逐字稿语料、个人记忆和真实数据。
- `skill-creator-prod/` 来自第三方，沿用其 Apache-2.0 许可，见该目录 LICENSE.txt。
- 课程制作技能默认在作者自己的工作区使用，路径与工具链请按你的环境调整。

## 保存与维护

- 今后工作区 Skill 统一放在本目录，一个技能一个子目录，主文件叫SKILL.md，配套资料与脚本随它保存在同目录。
- 新增/改名时同步更新本页和skills.json，并检查引用。
- 历史备份在.history/，不当作当前技能。
- 此目录用于查找制作方法；读取Skill不自动授予消费额度、发布、外发资料或删除文件的权限。
