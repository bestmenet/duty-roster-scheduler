from __future__ import annotations

from pathlib import Path, PurePosixPath
import zipfile
import xml.etree.ElementTree as ET

M = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P = 'http://schemas.openxmlformats.org/package/2006/relationships'


class XlsxReadError(RuntimeError):
    pass


def _sheet_map(z: zipfile.ZipFile) -> list[tuple[str, str]]:
    wb = ET.fromstring(z.read('xl/workbook.xml'))
    rr = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    rel = {x.attrib['Id']: x.attrib['Target'] for x in rr.findall(f'{{{P}}}Relationship')}
    sheets = wb.find(f'{{{M}}}sheets')
    if sheets is None:
        raise XlsxReadError('Workbook has no worksheets')
    out = []
    for s in sheets.findall(f'{{{M}}}sheet'):
        name = s.attrib.get('name', '')
        rid = s.attrib.get(f'{{{R}}}id')
        target = rel.get(rid)
        if not target:
            continue
        p = PurePosixPath(target)
        path = str(p).lstrip('/') if str(p).startswith('/') else str(PurePosixPath('xl') / p)
        out.append((name, path))
    if not out:
        raise XlsxReadError('Workbook has no readable worksheets')
    return out


def sheet_names(path: str | Path) -> list[str]:
    with zipfile.ZipFile(path) as z:
        return [name for name, _ in _sheet_map(z)]


def read_values(path: str | Path, sheet: str | None = None) -> tuple[dict[str, str], str]:
    path = Path(path)
    if not path.exists():
        raise XlsxReadError(f'File not found: {path}')
    with zipfile.ZipFile(path) as z:
        sheets = _sheet_map(z)
        chosen = None
        for name, sp in sheets:
            if sheet is None or name == sheet:
                chosen = (name, sp)
                break
        if chosen is None:
            raise XlsxReadError(f'Sheet not found: {sheet}')
        name, sp = chosen

        shared: list[str] = []
        if 'xl/sharedStrings.xml' in z.namelist():
            root = ET.fromstring(z.read('xl/sharedStrings.xml'))
            shared = [
                ''.join(t.text or '' for t in si.iter(f'{{{M}}}t'))
                for si in root.findall(f'{{{M}}}si')
            ]

        root = ET.fromstring(z.read(sp))
        out: dict[str, str] = {}
        for c in root.iter(f'{{{M}}}c'):
            cell = c.attrib.get('r')
            typ = c.attrib.get('t')
            if not cell:
                continue
            if typ == 'inlineStr':
                value = ''.join(t.text or '' for t in c.iter(f'{{{M}}}t'))
            else:
                ve = c.find(f'{{{M}}}v')
                raw = '' if ve is None or ve.text is None else ve.text
                if typ == 's' and raw:
                    try:
                        idx = int(raw)
                    except ValueError:
                        value = raw
                    else:
                        value = shared[idx] if 0 <= idx < len(shared) else raw
                else:
                    value = raw
            out[cell] = value
        return out, name
