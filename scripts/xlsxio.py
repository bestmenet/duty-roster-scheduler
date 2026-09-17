from pathlib import Path, PurePosixPath
from copy import deepcopy
import re, zipfile
import xml.etree.ElementTree as ET

M='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P='http://schemas.openxmlformats.org/package/2006/relationships'
X='http://www.w3.org/XML/1998/namespace'
ET.register_namespace('',M); ET.register_namespace('r',R)

class XlsxError(RuntimeError): pass

def _sheet(z,sheet=None):
    wb=ET.fromstring(z.read('xl/workbook.xml')); rr=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    rel={x.attrib['Id']:x.attrib['Target'] for x in rr.findall(f'{{{P}}}Relationship')}
    ss=wb.find(f'{{{M}}}sheets'); pick=None
    for s in ss.findall(f'{{{M}}}sheet'):
        if sheet is None or s.attrib.get('name')==sheet: pick=s; break
    if pick is None: raise XlsxError(f'Sheet not found: {sheet}')
    t=rel.get(pick.attrib.get(f'{{{R}}}id'))
    if not t: raise XlsxError('Missing worksheet relationship')
    p=PurePosixPath(t); path=str(p).lstrip('/') if str(p).startswith('/') else str(PurePosixPath('xl')/p)
    return path,pick.attrib.get('name','')

def read_values(path,sheet=None):
    with zipfile.ZipFile(path) as z:
        sp,name=_sheet(z,sheet); shared=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            root=ET.fromstring(z.read('xl/sharedStrings.xml'))
            shared=[''.join(t.text or '' for t in si.iter(f'{{{M}}}t')) for si in root.findall(f'{{{M}}}si')]
        root=ET.fromstring(z.read(sp)); out={}
        for c in root.iter(f'{{{M}}}c'):
            a=c.attrib.get('r'); typ=c.attrib.get('t')
            if not a: continue
            if typ=='inlineStr': v=''.join(t.text or '' for t in c.iter(f'{{{M}}}t'))
            else:
                e=c.find(f'{{{M}}}v'); raw='' if e is None or e.text is None else e.text
                v=shared[int(raw)] if typ=='s' and raw and int(raw)<len(shared) else raw
            out[a]=v
        return out,name

def _col(a):
    m=re.match(r'([A-Z]+)',a); n=0
    for ch in m.group(1): n=n*26+ord(ch)-64
    return n

def _wrap_style(styles_root, style_id, cache):
    if styles_root is None:return style_id
    xfs=styles_root.find(f'{{{M}}}cellXfs')
    if xfs is None or not list(xfs):return style_id
    if style_id in cache:return cache[style_id]
    if style_id<0 or style_id>=len(xfs):style_id=0
    xf=deepcopy(xfs[style_id])
    xf.attrib['applyAlignment']='1'
    alignment=xf.find(f'{{{M}}}alignment')
    if alignment is None:alignment=ET.SubElement(xf,f'{{{M}}}alignment')
    alignment.attrib['wrapText']='1'
    xfs.append(xf); xfs.attrib['count']=str(len(xfs))
    new_id=len(xfs)-1; cache[style_id]=new_id
    return new_id

def patch(template,output,cells,sheet='值班表模板'):
    output=Path(output); output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(template) as zin:
        sp,_=_sheet(zin,sheet); root=ET.fromstring(zin.read(sp)); sd=root.find(f'{{{M}}}sheetData')
        styles_path='xl/styles.xml'; styles_root=ET.fromstring(zin.read(styles_path)) if styles_path in zin.namelist() else None
        wrap_cache={}
        rows={int(r.attrib['r']):r for r in sd.findall(f'{{{M}}}row') if r.attrib.get('r')}
        def cell(addr):
            m=re.match(r'([A-Z]+)(\d+)$',addr); rn=int(m.group(2)); row=rows.get(rn)
            if row is None:
                row=ET.Element(f'{{{M}}}row',{'r':str(rn)}); sd.append(row); rows[rn]=row
            for c in row.findall(f'{{{M}}}c'):
                if c.attrib.get('r')==addr:return c
            c=ET.Element(f'{{{M}}}c',{'r':addr}); pos=len(row); cn=_col(addr)
            for i,e in enumerate(list(row)):
                if e.tag==f'{{{M}}}c' and _col(e.attrib.get('r','A1'))>cn: pos=i; break
            row.insert(pos,c); return c
        for a,text in cells.items():
            c=cell(a)
            old_style=int(c.attrib.get('s','0') or 0)
            c.attrib['s']=str(_wrap_style(styles_root,old_style,wrap_cache))
            for ch in list(c): c.remove(ch)
            c.attrib['t']='inlineStr'; isel=ET.SubElement(c,f'{{{M}}}is'); t=ET.SubElement(isel,f'{{{M}}}t')
            t.attrib[f'{{{X}}}space']='preserve'; t.text=text
        sheet_xml=ET.tostring(root,encoding='utf-8',xml_declaration=True)
        styles_xml=ET.tostring(styles_root,encoding='utf-8',xml_declaration=True) if styles_root is not None else None
        with zipfile.ZipFile(output,'w') as zout:
            for it in zin.infolist():
                if it.filename==sp:data=sheet_xml
                elif it.filename==styles_path and styles_xml is not None:data=styles_xml
                else:data=zin.read(it.filename)
                zout.writestr(it,data)

def validate_multiline_cells(path,expected,sheet='值班表模板'):
    issues=[]
    with zipfile.ZipFile(path) as z:
        sp,_=_sheet(z,sheet); root=ET.fromstring(z.read(sp))
        cells={c.attrib.get('r'):c for c in root.iter(f'{{{M}}}c') if c.attrib.get('r')}
        styles=ET.fromstring(z.read('xl/styles.xml')) if 'xl/styles.xml' in z.namelist() else None
        xfs=styles.find(f'{{{M}}}cellXfs') if styles is not None else None
        for addr,want in expected.items():
            c=cells.get(addr)
            if c is None:
                issues.append(f'{addr}:missing');continue
            got=''.join(t.text or '' for t in c.iter(f'{{{M}}}t'))
            if got!=want:issues.append(f'{addr}:value-mismatch')
            if '\n' not in got:issues.append(f'{addr}:missing-line-break')
            sid=int(c.attrib.get('s','0') or 0)
            wrapped=False
            if xfs is not None and 0<=sid<len(xfs):
                alignment=xfs[sid].find(f'{{{M}}}alignment')
                wrapped=alignment is not None and alignment.attrib.get('wrapText') in {'1','true','True'}
            if not wrapped:issues.append(f'{addr}:wrapText-off')
    return issues
