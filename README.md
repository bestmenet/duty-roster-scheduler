# duty-roster-scheduler

一个**通用、只读、即用即弃**的值班表验证 Agent Skill。

仓库名称保留为 `duty-roster-scheduler` 以兼容现有安装方式，但当前功能已经改为：**仅验证现有值班表，不再生成或修改值班表。**

## 核心限制

本 Skill 只能用于值班表验证。

它不会、也不允许：

- 自动排班；
- 生成新的 Excel；
- 修改已有人员安排；
- 修复单元格换行；
- 调整字体、边框、行高、列宽、合并单元格等排版；
- 输出“修正版”工作簿。

验证时只读取三个输入：**第几周、无课表 Excel、待验证值班表 Excel**。

所有人员和空闲信息都从用户本次提供的文件中读取。仓库中不保存固定人员名单，也不写任何针对具体个人的可排 / 禁排规则。

## 可验证内容

- 单周 / 双周是否匹配；
- 每个值班格是否使用真实单元格内换行；
- 第一行与第二行的结构是否正确；
- 人员是否与无课表冲突；
- 是否存在未知人员；
- 是否存在同一格重复人员；
- 是否存在第一行 / 第二行角色混用；
- 1-2 节是否违规增员；
- 增员时段是否超过约三分之一；
- 是否存在同一人同一天多次值班；
- 值班频次是否明显超过通用上限。

字体、颜色、边框、尺寸、合并、打印设置等视觉排版不在本 Skill 的处理范围内。

## 安装

```bash
npx skills add bestmenet/duty-roster-scheduler -g -y
```

## 使用

```bash
python scripts/validate_roster.py \
  --week 4 \
  --free-table "/path/to/无课表（双周）.xlsx" \
  --roster "/path/to/第四周值班表.xlsx" \
  --report "/safe/output/第四周值班表_验证.json"
```

验证脚本只读取 Excel。不会保存、覆盖或修改任何 `.xlsx`。

退出状态：

- `0`：验证通过并成功完成自清理；
- `3`：发现验证错误，但验证已完成且自清理成功；
- `4`：验证已完成，但 Skill 自动删除失败；
- `2`：输入或文件解析错误，未完成有效验证。

## 即用即弃

完成一次实际验证后，`validate_roster.py` 会自动调用 `scripts/cleanup_skill.py` 删除本地 Skill，并验证删除结果。

验证是否通过不影响清理：**只要完成了验证，就立即删除 Skill。**

清理只针对本地安装副本，不删除：

- GitHub 仓库；
- 无课表；
- 待验证值班表；
- JSON 验证报告。

## 目录

```text
duty-roster-scheduler/
├─ SKILL.md
├─ README.md
├─ INSTALL_PROMPT.md
├─ config/
│  └─ settings.json
├─ references/
│  └─ rules.md
└─ scripts/
   ├─ validate_roster.py
   ├─ xlsx_reader.py
   ├─ cleanup_skill.py
   └─ README.md
```
