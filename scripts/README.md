# Scripts

- `generate_roster.py`: CLI 入口，读取周数和无课表，生成新的排班 Excel 与 JSON 校验报告；成功完成后自动调用 `cleanup_skill.py` 删除本地 Skill 并验证删除结果。
- `cleanup_skill.py`: 即用即弃清理器。优先使用 Skills CLI 删除全局/项目级 `duty-roster-scheduler`，随后验证；必要时仅对名称精确匹配的本地 Skill 根目录做兜底删除，并保护带 `.git` 的源码仓库。
- `scheduler.py`: 可用时段解析、均衡排班、增员分配。
- `xlsxio.py`: 直接修改 OOXML，保留原 Excel 模板格式。
