#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET

from xlsx_reader import read_values, sheet_names, XlsxReadError

SKILL_NAME = 'duty-roster-scheduler'
DAYS = ['星期一', '星期二', '星期三', '星期四', '星期五']
DAY_ALIASES = [
    {'星期一', '周一'}, {'星期二', '周二'}, {'星期三', '周三'}, {'星期四', '周四'}, {'星期五', '周五'}
]
SLOTS = [
    ('1-2', (0, 1)),
    ('3-4', (2, 3)),
    ('5-6', (4, 5)),
    ('7-8', (6, 7)),
    ('9-10', None),
]
PLACEHOLDERS = {'待补', '待定', '空缺', '暂无'}
NAME_SPLIT_RE = re.compile(r'[、,，;；]+')


class ValidationRuntimeError(RuntimeError):
    pass


def col_letters(n: int) -> str:
    out = ''
    while n:
        n, r = divmod(n - 1, 26)
        out = chr(65 + r) + out
    return out


def addr(row: int, col: int) -> str:
    return f'{col_letters(col)}{row}'


def normalized_text(value: str | None) -> str:
    return (value or '').replace('\u3000', ' ').strip()


def day_value(value: str | None) -> str:
    return re.sub(r'\s+', '', normalized_text(value))


def find_weekday_header(values: dict[str, str], max_rows: int = 20, max_cols: int = 20) -> tuple[int, int]:
    for row in range(1, max_rows + 1):
        for start_col in range(1, max_cols - 4 + 1):
            if all(day_value(values.get(addr(row, start_col + i))) in DAY_ALIASES[i] for i in range(5)):
                return row, start_col
    raise ValidationRuntimeError('未找到连续的星期一到星期五表头')


def read_weekday_table(path: Path) -> tuple[dict[str, str], str, int, int]:
    last_error = None
    for name in sheet_names(path):
        values, _ = read_values(path, name)
        try:
            row, col = find_weekday_header(values)
            return values, name, row, col
        except ValidationRuntimeError as exc:
            last_error = exc
    raise ValidationRuntimeError(f'{path.name} 中未找到可识别的星期一到星期五表格') from last_error


def title_text(values: dict[str, str], max_rows: int = 4, max_cols: int = 12) -> str:
    parts = []
    for row in range(1, max_rows + 1):
        for col in range(1, max_cols + 1):
            value = normalized_text(values.get(addr(row, col)))
            if value:
                parts.append(value)
    return ' '.join(parts)


def split_free_entries(text: str | None) -> list[tuple[str, str | None]]:
    raw = normalized_text(text).replace('\r\n', '\n').replace('\r', '\n')
    if not raw:
        return []
    entries = []
    for part in re.split(r'[、\n]+', raw):
        part = part.strip()
        if not part:
            continue
        match = re.fullmatch(r'(.+?)(?:[（(]([^）)]+)[）)])?', part)
        if not match:
            continue
        name = match.group(1).strip()
        spec = match.group(2).strip() if match.group(2) else None
        if name:
            entries.append((name, spec))
    return entries


def week_allowed(spec: str | None, week: int) -> bool:
    if not spec:
        return True
    text = spec.replace('—', '~').replace('–', '~').replace('-', '~').replace('至', '~')
    for token in re.split(r'[，,、;；\s]+', text):
        token = token.strip()
        if not token:
            continue
        match = re.fullmatch(r'(\d+)\s*~\s*(\d+)', token)
        if match and int(match.group(1)) <= week <= int(match.group(2)):
            return True
        if token.isdigit() and int(token) == week:
            return True
    return False


def free_names(text: str | None, week: int) -> set[str]:
    return {name for name, spec in split_free_entries(text) if week_allowed(spec, week)}


def all_names(text: str | None) -> set[str]:
    return {name for name, _ in split_free_entries(text)}


def split_people_line(line: str) -> list[str]:
    return [part.strip() for part in NAME_SPLIT_RE.split(line) if part.strip()]


def parse_roster_cell(text: str | None, require_line_break: bool) -> dict:
    raw = normalized_text(text).replace('\r\n', '\n').replace('\r', '\n')
    result = {'raw': raw, 'first': [], 'second': [], 'issues': []}
    if not raw:
        result['issues'].append(('error', 'empty_slot', '值班格为空'))
        return result
    if require_line_break and '\n' not in raw:
        result['issues'].append(('error', 'missing_line_break', '值班格没有使用真实的单元格内换行分隔第一行和第二行'))
        return result
    lines = [line.strip() for line in raw.split('\n') if line.strip()]
    if len(lines) != 2:
        result['issues'].append(('error', 'invalid_line_count', f'值班格应恰好有两行，当前为 {len(lines)} 行'))
        return result
    first = split_people_line(lines[0])
    second = split_people_line(lines[1])
    if len(first) != 1:
        result['issues'].append(('error', 'invalid_first_line', '第一行必须且只能有 1 人或占位符'))
    if len(second) not in (1, 2):
        result['issues'].append(('error', 'invalid_second_line', '第二行必须有 1 人，允许增员时最多 2 人'))
    result['first'] = first
    result['second'] = second
    return result


def is_within(path: Path, root: Path) -> bool:
    try:
        path.expanduser().resolve().relative_to(root.expanduser().resolve())
        return True
    except ValueError:
        return False


def run_cleanup(skill_root: Path, project_dir: Path) -> dict:
    cleanup_script = skill_root / 'scripts' / 'cleanup_skill.py'
    if is_within(Path.cwd(), skill_root):
        try:
            os.chdir(tempfile.gettempdir())
        except OSError as exc:
            return {'verified_removed': False, 'error': f'无法离开 Skill 目录以执行自清理: {exc}'}
    if not cleanup_script.exists():
        return {'verified_removed': False, 'error': '缺少自动清理脚本 cleanup_skill.py'}
    cmd = [sys.executable, str(cleanup_script), '--skill-name', SKILL_NAME, '--skill-root', str(skill_root)]
    if project_dir and not is_within(project_dir, skill_root):
        cmd += ['--project-dir', str(project_dir)]
    try:
        cp = subprocess.run(cmd, cwd=tempfile.gettempdir(), text=True, capture_output=True, timeout=180, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return {'verified_removed': False, 'error': str(exc)}
    try:
        payload = json.loads(cp.stdout) if cp.stdout.strip() else {}
    except json.JSONDecodeError:
        payload = {'stdout': cp.stdout[-4000:]}
    payload['returncode'] = cp.returncode
    if cp.stderr.strip():
        payload['stderr'] = cp.stderr[-4000:]
    payload['verified_removed'] = bool(payload.get('verified_removed')) and cp.returncode == 0
    return payload


def issue(severity: str, code: str, message: str, **extra) -> dict:
    return {'severity': severity, 'code': code, 'message': message, **extra}


def validate(week: int, free_table: Path, roster: Path, settings: dict) -> dict:
    free_vals, free_sheet, free_header_row, free_start_col = read_weekday_table(free_table)
    roster_vals, roster_sheet, roster_header_row, roster_start_col = read_weekday_table(roster)

    issues: list[dict] = []
    free_title = title_text(free_vals)
    if '单周' in free_title and week % 2 == 0:
        issues.append(issue('error', 'week_type_mismatch', f'第 {week} 周为双周，但无课表标题显示为单周'))
    if '双周' in free_title and week % 2 == 1:
        issues.append(issue('error', 'week_type_mismatch', f'第 {week} 周为单周，但无课表标题显示为双周'))

    known_people: set[str] = set()
    period_free: dict[tuple[int, int], set[str]] = {}
    for day in range(5):
        col = free_start_col + day
        for period in range(8):
            cell = addr(free_header_row + 1 + period, col)
            known_people |= all_names(free_vals.get(cell))
            period_free[day, period] = free_names(free_vals.get(cell), week)

    tuesday_break = bool(settings.get('tuesday_afternoon_public_break', True))
    evening_default = bool(settings.get('evening_is_default_free', True))
    require_line_break = bool(settings.get('require_real_line_break', True))
    no_extra_slots = set(settings.get('no_extra_slots', ['1-2']))

    slot_records = []
    first_counts = Counter()
    second_counts = Counter()
    person_day_slots: dict[tuple[str, int], list[str]] = defaultdict(list)
    extra_slots = 0

    for day in range(5):
        for slot_index, (slot_name, period_pair) in enumerate(SLOTS):
            cell = addr(roster_header_row + 1 + slot_index, roster_start_col + day)
            parsed = parse_roster_cell(roster_vals.get(cell), require_line_break)
            for severity, code, message in parsed['issues']:
                issues.append(issue(severity, code, message, cell=cell, day=DAYS[day], slot=slot_name))

            first = parsed['first']
            second = parsed['second']
            if len(second) == 2:
                extra_slots += 1
                if slot_name in no_extra_slots:
                    issues.append(issue('error', 'extra_not_allowed', f'{slot_name} 节禁止增员', cell=cell, day=DAYS[day], slot=slot_name))

            people = []
            for person in first:
                if person not in PLACEHOLDERS:
                    first_counts[person] += 1
                    people.append(person)
                else:
                    issues.append(issue('error', 'unfilled_first_line', '第一行仍为待补/待定状态', cell=cell, day=DAYS[day], slot=slot_name))
            for person in second:
                if person not in PLACEHOLDERS:
                    second_counts[person] += 1
                    people.append(person)
                else:
                    issues.append(issue('error', 'unfilled_second_line', '第二行仍为待补/待定状态', cell=cell, day=DAYS[day], slot=slot_name))

            if len(set(people)) != len(people):
                issues.append(issue('error', 'duplicate_within_slot', '同一值班格内出现重复人员', cell=cell, day=DAYS[day], slot=slot_name))

            if period_pair is None and evening_default:
                available = set(known_people)
            elif day == 1 and slot_name in {'5-6', '7-8'} and tuesday_break:
                available = set(known_people)
            elif period_pair is None:
                available = set()
            else:
                a, b = period_pair
                available = period_free[day, a] & period_free[day, b]

            for person in people:
                person_day_slots[person, day].append(slot_name)
                if person not in known_people:
                    issues.append(issue('error', 'unknown_person', '该人员未出现在无课表中，无法验证空闲状态', cell=cell, day=DAYS[day], slot=slot_name, person=person))
                elif person not in available:
                    issues.append(issue('error', 'schedule_conflict', '该人员在此时段不满足无课条件', cell=cell, day=DAYS[day], slot=slot_name, person=person))

            slot_records.append({'cell': cell, 'day': DAYS[day], 'slot': slot_name, 'first': first, 'second': second})

    for person in sorted(set(first_counts) & set(second_counts)):
        issues.append(issue('error', 'role_mixed', '同一人员同时出现在第一行角色与第二行角色中', person=person))

    if settings.get('avoid_same_person_twice_same_day', True):
        for (person, day), slots in sorted(person_day_slots.items()):
            if len(slots) > 1:
                issues.append(issue('warning', 'same_day_repeat', '同一人员同一天出现多次值班', person=person, day=DAYS[day], slots=slots))

    first_max = int(settings.get('first_line_normal_max', 3))
    second_max = int(settings.get('second_line_normal_max', 2))
    for person, count in sorted(first_counts.items()):
        if count > first_max:
            issues.append(issue('warning', 'first_line_frequency_high', f'第一行角色本周出现 {count} 次，高于常规上限 {first_max}', person=person, count=count))
    for person, count in sorted(second_counts.items()):
        if count > second_max:
            issues.append(issue('warning', 'second_line_frequency_high', f'第二行角色本周出现 {count} 次，高于常规上限 {second_max}', person=person, count=count))

    total_slots = len(slot_records)
    extra_cap = round(total_slots * float(settings.get('extra_slot_fraction_cap', 1 / 3)))
    if extra_slots > extra_cap:
        issues.append(issue('error', 'too_many_extra_slots', f'增员时段共 {extra_slots} 个，超过约三分之一的上限 {extra_cap}', count=extra_slots, cap=extra_cap))

    errors = sum(1 for item in issues if item['severity'] == 'error')
    warnings = sum(1 for item in issues if item['severity'] == 'warning')
    return {
        'scope': 'validation_only',
        'week': week,
        'free_table': str(free_table),
        'free_table_sheet': free_sheet,
        'roster': str(roster),
        'roster_sheet': roster_sheet,
        'summary': {
            'passed': errors == 0,
            'errors': errors,
            'warnings': warnings,
            'slots_checked': total_slots,
            'extra_slots': extra_slots,
            'extra_slot_cap': extra_cap,
            'known_people_count': len(known_people),
        },
        'counts': {
            'first_line': dict(sorted(first_counts.items())),
            'second_line': dict(sorted(second_counts.items())),
        },
        'issues': issues,
    }


def main() -> int:
    skill_root = Path(__file__).absolute().parent.parent
    project_dir = Path.cwd().absolute()
    parser = argparse.ArgumentParser(description='Read-only duty roster validator. Never edits or reformats spreadsheets.')
    parser.add_argument('--week', type=int, required=True)
    parser.add_argument('--free-table', type=Path, required=True)
    parser.add_argument('--roster', type=Path, required=True)
    parser.add_argument('--settings', type=Path, default=skill_root / 'config' / 'settings.json')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if args.week <= 0:
        parser.error('--week must be positive')

    report = args.report.expanduser().absolute() if args.report else None
    if report and is_within(report, skill_root):
        parser.error('report must be outside the skill directory because the skill self-deletes after use')

    try:
        config = json.loads(args.settings.read_text(encoding='utf-8'))
        result = validate(
            args.week,
            args.free_table.expanduser().absolute(),
            args.roster.expanduser().absolute(),
            config.get('validation', {}),
        )
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, ET.ParseError, XlsxReadError, ValidationRuntimeError) as exc:
        payload = {'ok': False, 'validated': False, 'scope': 'validation_only', 'error': str(exc)}
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2

    cleanup = run_cleanup(skill_root, project_dir)
    result['cleanup'] = cleanup
    result['ok'] = bool(result['summary']['passed']) and bool(cleanup.get('verified_removed'))

    if report:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')

    stream = sys.stdout if result['ok'] else sys.stderr
    print(json.dumps(result, ensure_ascii=False, indent=2), file=stream)
    if not cleanup.get('verified_removed'):
        return 4
    return 0 if result['summary']['passed'] else 3


if __name__ == '__main__':
    raise SystemExit(main())
