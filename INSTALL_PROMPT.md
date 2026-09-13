# 一键安装 Prompt

把下面这段直接发给 Codex / Claude Code / 支持 Agent Skills 的编码代理：

> 请安装并启用这个 Agent Skill：`https://github.com/bestmenet/duty-roster-scheduler`。优先使用 Skills CLI 执行 `npx skills add bestmenet/duty-roster-scheduler -g -y`。安装完成后读取该 Skill 的 `SKILL.md`，以后当我要求“根据第几周和无课表生成值班表”时，严格按照该 Skill 的模板、排班限制与验证流程执行。

也可以直接执行：

```bash
npx skills add bestmenet/duty-roster-scheduler -g -y
```
