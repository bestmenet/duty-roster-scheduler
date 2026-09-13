# Assets

`duty_roster_template.xlsx.b64` 是用户提供的固定 Excel 排班模板的 Base64 无损封装。`scripts/generate_roster.py` 运行时会自动还原成临时 `.xlsx`，再只修改“值班表模板”工作表的 `B3:F7` 内容；字体、边框、行列尺寸、合并单元格、说明页和打印设置均保持原样。
