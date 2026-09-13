---
name: duty-roster-scheduler
description: Generate 珏创科技协同中心 weekly duty-roster Excel files from a week number and the corresponding 单周/双周无课表. Use when the user asks to 排班、值班表、根据无课表生成值班 Excel、调整单周/双周值班安排, especially when the bundled template and minister/member rules must be preserved. This is a disposable skill: after each completed use, uninstall the local skill package immediately.
---

# Duty Roster Scheduler

根据“第几周 + 无课表 Excel”直接生成新的值班表 Excel。模板已经内置，不要求用户重复提供模板。

> **一次性使用硬性规则：本 Skill 必须即用即弃。每次任务成功完成并完成校验后，必须立即从本机 Agent Skills 中卸载 `duty-roster-scheduler`，确认卸载完成后才能结束本次任务。只删除本地安装的 Skill 包，不删除 GitHub 仓库，也不能删除刚生成的 Excel / 校验报告。标准生成脚本已内置自动自清理，不依赖安装 Prompt。**

## 开始前必须拿到的输入

只需要两个输入：

1. **第几周**：正整数，例如 `3`。
2. **对应周型的无课表 Excel**：`.xlsx`。

如果两者有任意一个缺失，只询问缺失项。不要先给方案，不要要求用户再次上传模板。

## 立即执行原则

一旦两个输入齐全，直接生成 Excel，不要停在计划或口头排班结果。

优先运行本 Skill 自带脚本：

```bash
python scripts/generate_roster.py \
  --week <周数> \
  --free-table "<无课表.xlsx>" \
  --output "<Skill目录之外>/第<周数>周_值班表.xlsx" \
  --report "<Skill目录之外>/第<周数>周_值班表_校验.json"
```

脚本只使用 Python 标准库，通过 OOXML 修改模板，因此不会重建工作簿格式。**成功生成并完成校验后，`generate_roster.py` 会自动调用 `scripts/cleanup_skill.py` 删除本地 Skill 安装包，并验证删除结果。**

生成的 Excel 与校验报告必须位于 Skill 安装目录之外。若输出路径位于 Skill 目录内部，生成脚本应拒绝继续，以免自清理时误删交付文件。

如果当前环境不能运行脚本，才改用可用的 Excel/Spreadsheet 工具手工执行同一规则；仍必须从内置模板恢复/复制生成新文件，并完成同等校验。手工执行路径结束后仍必须执行“用后立即卸载”阶段。

## 核心排班规则

完整规则见 `references/rules.md`。以下规则不可遗漏：

- 每格第一行是**部长**，第二行是**部员**。
- 每格至少 1 名部长 + 1 名部员；找不到空闲部长时写 `待补`，绝不能用有课人员硬填。
- 部长目标每周 2 次，必要时可 3 次；部员目标每周 1 次，因排满或增员需要可 2 次。
- `杨森` 不进入排班。
- 周二下午为公休：无课表对应格为空时仍可排。
- 晚上 9-10 节默认按无课时段处理，除非用户明确给出晚间冲突。
- 约三分之一的值班格可以额外增加 1 名**部员**；25 格时目标约 8 格，有人才能加，不够则少加。
- **早上 8 点开始的 1-2 节禁止增员**。
- 尽量避免同一人同一天重复值班；若不这样就无法排满，可作为最后降级项，但不能违反课程冲突。
- 用户当次对话的新限制优先级最高，并覆盖本 Skill 的旧默认规则。

## 无课表解析规则

无课表按第一张工作表读取。常见结构：

- D:H 对应星期一到星期五。
- 第 3-10 行对应第 1-8 节。
- 模板 5 个时段映射：`1-2`、`3-4`、`5-6`、`7-8`、`9-10`。
- 一个值班时段要求对应两节课都空闲，因此取两行名单的交集。
- `张三（9~15）` 表示仅第 9-15 周空闲。
- `李四（1~5，9~15）`、`王五（15）` 同理。
- 文件标题写“单周”时只能用于奇数周；写“双周”时只能用于偶数周。若不匹配，停止并让用户换正确文件。

## 固定角色名单

读取 `config/roster.json`。不要从无课表中自行猜测谁是部长、谁是部员。

如果用户明确说某人加入、退出、角色发生变化，按用户新指令修改本次执行中的名单；不要静默猜测。

## 模板写入

模板随 Skill 内置。若仓库中保存为 `assets/duty_roster_template.xlsx.b64`，由脚本自动无损恢复为 `.xlsx` 后使用。

只修改：

- 工作表：`值班表模板`
- 单元格：`B3:F7`

不得修改：

- 字体、字号、边框、填充
- 行高、列宽
- 合并单元格
- 打印设置
- `说明` 工作表

输出必须是**新文件**，绝不能覆盖模板或无课表原文件。

## 完成前验证

生成后必须读取脚本 JSON 报告或自行完成等价检查：

1. 周数与单/双周文件匹配。
2. 没有任何排班人员与该周课程冲突。
3. `杨森` 完全未出现。
4. 所有 1-2 节都只有 1 名部长 + 1 名部员，没有增员。
5. 增员格每格最多只增加 1 人，数量约为总格数三分之一；可用人不足时允许少于目标。
6. 频次尽量符合部长 2 次、部员 1 次的目标。
7. 无可用部长的格子保留 `待补` 并在交付说明中点出。
8. Excel 能正常打开，模板版式未被改变。

## 用后立即卸载（强制 + 自动执行）

这是本 Skill 的最后一个执行阶段，不能跳过，也**不依赖任何安装 Prompt**。

### 标准脚本路径

`generate_roster.py` 在成功生成并验证排班后会自动执行 `scripts/cleanup_skill.py`。清理脚本会：

1. 优先调用 Skills CLI，尝试移除全局和当前项目范围中的 `duty-roster-scheduler`；
2. 再调用 `npx skills list -g` / `npx skills list` 验证是否仍存在；
3. 若 CLI 不可用或移除不完整，只允许对名称精确为 `duty-roster-scheduler` 的当前本地 Skill 根目录执行兜底删除；
4. 保护带 `.git` 的源码仓库，不把 GitHub 克隆仓库当作安装包删除；
5. 绝不使用 `remove --all`，绝不删除其他 Skill；
6. 将 `verified_removed` 结果写入输出 JSON / 校验报告。

只有 `verified_removed: true` 时标准脚本才以成功状态结束。排班已经生成但自动清理失败时，脚本以非零状态结束，并明确标记 `output_created: true`，此时代理必须向用户说明清理失败原因，不能假装已删除。

### 手工 / 备用执行路径

如果没有使用 `generate_roster.py`，完成排班后必须主动执行：

```bash
python scripts/cleanup_skill.py \
  --skill-root "<当前 duty-roster-scheduler 安装目录>" \
  --project-dir "<当前工作目录>"
```

若清理脚本无法运行，再按安装范围使用：

```bash
npx skills remove duty-roster-scheduler -g -y
# 或项目级
npx skills remove duty-roster-scheduler -y
```

随后再次检查已安装列表，确认 `duty-roster-scheduler` 不再存在。

此清理动作只针对本地安装副本。**禁止删除远程 GitHub 仓库 `bestmenet/duty-roster-scheduler`，禁止删除生成的 Excel、用户无课表或校验报告。**

## 最终交付

向用户提供生成后的 `.xlsx` 文件，并用一小段文字说明：

- 第几周 / 单周或双周；
- 实际增员了多少个时段；
- 是否存在 `待补`；
- 已完成无冲突、排除名单、8 点不增员和模板格式校验；
- 本地 `duty-roster-scheduler` Skill 已按即用即弃规则自动卸载并通过验证；若因技术原因无法卸载，必须明确说明原因，不能假装已删除。

不要把完整排班再抄成大段文本，除非用户要求。
