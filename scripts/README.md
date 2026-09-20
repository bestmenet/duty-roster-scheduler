# Scripts

本目录只保留**只读验证**和自清理能力。

- `validate_roster.py`：主入口。读取第几周、无课表和现有值班表，执行通用验证；不写入任何 Excel。验证完成后自动执行自清理。
- `xlsx_reader.py`：只读解析 `.xlsx` 文本值，不包含任何写入、格式修改或另存功能。
- `cleanup_skill.py`：即用即弃清理器。删除本地 `duty-roster-scheduler` 并验证删除结果，保护 Git 仓库与用户文件。

本目录中不应出现生成排班、修改 OOXML、设置样式、修复格式或写回工作簿的代码。
