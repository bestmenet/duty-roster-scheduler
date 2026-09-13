# 一键安装 Prompt

把下面这段直接发给 Codex / Claude Code / 支持 Agent Skills 的编码代理：

> 请一次性安装并使用这个 Agent Skill：`https://github.com/bestmenet/duty-roster-scheduler`。优先使用 Skills CLI 执行 `npx skills add bestmenet/duty-roster-scheduler -g -y`。安装完成后读取该 Skill 的 `SKILL.md`，根据我提供的“第几周 + 无课表 Excel”生成并校验新的值班表。该 Skill 自身已经包含“即用即弃”的硬性规则和自动清理脚本：标准 `generate_roster.py` 在成功生成并校验 Excel 后会自动调用 `cleanup_skill.py` 删除本地 `duty-roster-scheduler` 安装包并验证删除结果，因此这个限制不依赖本 Prompt。生成的 Excel 和校验报告必须保存在 Skill 安装目录之外。只删除本地 Skill 安装副本，不删除远程 GitHub 仓库、生成的 Excel、用户提供的无课表或校验报告。若自动清理失败，必须明确报告原因，不能假装已删除。

安装命令：

```bash
npx skills add bestmenet/duty-roster-scheduler -g -y
```

正常情况下无需手动卸载；标准生成脚本会自动完成。只有自动清理脚本无法执行时，才手动使用：

```bash
npx skills remove duty-roster-scheduler -g -y
```
