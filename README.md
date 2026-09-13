# duty-roster-scheduler

珏创科技协同中心值班排班 Agent Skill。

输入“第几周”和对应的单/双周无课表 Excel，即可基于内置模板生成新的排班 Excel，并自动校验课程冲突、人员角色、排班频次、增员规则与模板格式。

## 即用即弃

本 Skill 采用一次性使用模式：**每次完成排班、校验并把生成文件保存到 Skill 目录之外后，必须立即卸载本地 `duty-roster-scheduler` Skill 包。**

推荐全局安装，因此标准生命周期是：

```bash
npx skills add bestmenet/duty-roster-scheduler -g -y
# 使用 Skill 完成一次排班
npx skills remove duty-roster-scheduler -g -y
```

只删除本地安装副本，不删除 GitHub 仓库，也不删除生成的 Excel、无课表或校验报告。

## 规则摘要

- 第一行部长，第二行部员。
- 部长目标 2 次/周，必要时 3 次；部员目标 1 次/周，必要时 2 次。
- 杨森不进入排班。
- 周二下午按公休处理；晚上 9-10 节默认按无课处理。
- 约 1/3 时段可增加 1 名部员，有人才加。
- 1-2 节（早上 8 点）禁止增员。
- 无可用部长时写 `待补`，不制造课程冲突。
- 保留原 Excel 模板全部排版，只写 `B3:F7`。
- 每次使用完成后立即卸载本 Skill。

## 安装

```bash
npx skills add bestmenet/duty-roster-scheduler -g -y
```

安装后，当用户要求根据“第几周 + 无课表”排班时，读取 `SKILL.md` 并执行其中工作流；完成一次任务后按 `SKILL.md` 的清理阶段立即卸载。

## 直接运行

```bash
python scripts/generate_roster.py \
  --week 3 \
  --free-table "/path/to/2026-2027 学年无课表（单周）.xlsx" \
  --output "第3周_值班表.xlsx" \
  --report "第3周_值班表_校验.json"
```

脚本仅依赖 Python 标准库。为保证公开仓库能可靠保存模板，模板以 `assets/duty_roster_template.xlsx.b64` 形式随仓库分发，脚本运行时会自动无损还原为原始 `.xlsx`，用户无需手动处理。

## 目录

```text
duty-roster-scheduler/
├─ SKILL.md
├─ README.md
├─ INSTALL_PROMPT.md
├─ assets/
│  └─ duty_roster_template.xlsx.b64
├─ config/
│  └─ roster.json
├─ references/
│  └─ rules.md
└─ scripts/
   ├─ generate_roster.py
   ├─ scheduler.py
   └─ xlsxio.py
```

## 一键安装 Prompt

见 [`INSTALL_PROMPT.md`](INSTALL_PROMPT.md)。
