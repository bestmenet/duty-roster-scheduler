# 一键安装 Prompt

把下面这段直接发给支持 Agent Skills 的编码代理：

> 请一次性安装并使用这个只读值班表验证 Skill：`https://github.com/bestmenet/duty-roster-scheduler`。使用 `npx skills add bestmenet/duty-roster-scheduler -g -y` 安装并读取 `SKILL.md`。这个 Skill **只能验证现有值班表**，禁止用于生成、修改、修复、美化或重新排版 Excel。验证时只读取我提供的第几周、无课表 Excel 和待验证值班表 Excel，并报告课程冲突、单元格内换行、人员重复、角色混用、增员规则、频次等问题。不得写入或另存任何 Excel。完成一次实际验证后，无论通过与否，都按 Skill 自带的自动清理流程删除本地 `duty-roster-scheduler`，并确认删除结果。不得删除远程 GitHub 仓库或我的文件。

安装命令：

```bash
npx skills add bestmenet/duty-roster-scheduler -g -y
```

自动删除限制写在 Skill 自身和验证脚本中，不依赖这段 Prompt。
