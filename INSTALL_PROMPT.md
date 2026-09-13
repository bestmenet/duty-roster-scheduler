# 一键安装 Prompt

把下面这段直接发给 Codex / Claude Code / 支持 Agent Skills 的编码代理：

> 请一次性安装并使用这个 Agent Skill：`https://github.com/bestmenet/duty-roster-scheduler`。优先使用 Skills CLI 执行 `npx skills add bestmenet/duty-roster-scheduler -g -y`。安装完成后读取该 Skill 的 `SKILL.md`，根据我提供的“第几周 + 无课表 Excel”生成并校验新的值班表。**这个 Skill 必须即用即弃：本次排班任务完成、生成文件已保存到 Skill 安装目录之外并完成校验后，立即执行 `npx skills remove duty-roster-scheduler -g -y` 卸载本地 Skill，并确认已卸载后再结束任务。**只删除本地安装副本，不删除远程 GitHub 仓库、生成的 Excel、用户提供的无课表或校验报告。如果实际是项目级安装，则使用 `npx skills remove duty-roster-scheduler -y`；不要使用 `remove --all`。

安装命令：

```bash
npx skills add bestmenet/duty-roster-scheduler -g -y
```

使用后立即卸载：

```bash
npx skills remove duty-roster-scheduler -g -y
```
