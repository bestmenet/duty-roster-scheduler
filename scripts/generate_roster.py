#!/usr/bin/env python3
from pathlib import Path
from collections import defaultdict
import argparse,base64,binascii,json,sys,tempfile,zipfile
import xml.etree.ElementTree as ET
from xlsxio import read_values,patch,XlsxError
from scheduler import availability,assign,extras,DAYS,TC

class RosterError(RuntimeError):pass

def resolve_template(template):
    template=Path(template)
    if template.exists():return template,None
    encoded=Path(str(template)+'.b64')
    if not encoded.exists():raise RosterError(f'找不到排班模板: {template} 或 {encoded}')
    holder=tempfile.TemporaryDirectory(prefix='duty-roster-template-')
    decoded=Path(holder.name)/template.name
    try:decoded.write_bytes(base64.b64decode(encoded.read_text(encoding='utf-8').strip(),validate=True))
    except (binascii.Error,ValueError) as e:
        holder.cleanup();raise RosterError(f'内置模板解码失败: {e}')
    return decoded,holder

def generate(week,free,template,config_path,output):
    c=json.loads(Path(config_path).read_text(encoding='utf-8')); ex=set(c.get('excluded',[])); st=c.get('settings',{})
    mins=[x for x in c['ministers'] if x not in ex]; mem=[x for x in c['members'] if x not in ex]; people=set(mins)|set(mem)
    vals,sh=read_values(free); title=vals.get('B1','') or vals.get('A1','')
    if '单周' in title and week%2==0:raise RosterError(f'第 {week} 周是双周，但文件标题显示为单周无课表')
    if '双周' in title and week%2==1:raise RosterError(f'第 {week} 周是单周，但文件标题显示为双周无课表')
    slots,av=availability(vals,week,people,st); av=[a-ex for a in av]
    ma,mu=assign(slots,av,mins,week,int(st.get('minister_target_per_week',2)),int(st.get('minister_normal_cap',3)),st.get('avoid_same_person_twice_same_day',True))
    ba,bu=assign(slots,av,mem,week,int(st.get('member_target_per_week',1)),int(st.get('member_normal_cap',2)),st.get('avoid_same_person_twice_same_day',True))
    extra=extras(slots,av,mem,ba,ma,week,round(len(slots)*float(st.get('extra_slot_fraction',1/3))))
    cells={}
    for i,s in enumerate(slots):
        member=ba.get(i,'待补')+((f'、{extra[i]}') if i in extra else '')
        cells[f"{TC[s['day_idx']]}{s['row']}"]=f"{ma.get(i,'待补')}\n{member}"
    patch(template,output,cells)
    out,_=read_values(output,'值班表模板')
    if any(not out.get(a) for a in cells):raise RosterError('输出文件写入失败')
    for data in (ma,ba,extra):
        for i,p in data.items():
            if p not in av[i]:raise RosterError(f'内部校验发现课表冲突: {p} {slots[i]}')
            if p in ex:raise RosterError('排班中出现排除名单人员')
    if any(slots[i]['name']=='1-2' for i in extra):raise RosterError('1-2 节出现增员')
    mc=defaultdict(int);bc=defaultdict(int)
    for p in ma.values():mc[p]+=1
    for p in ba.values():bc[p]+=1
    for p in extra.values():bc[p]+=1
    rep=[]
    for role,data in [('minister',ma),('member',ba),('extra',extra)]:
        seen=defaultdict(list)
        for i,p in data.items():seen[p,slots[i]['day_idx']].append(slots[i]['name']+('(增员)' if role=='extra' else ''))
        if role=='extra':
            for i,p in ba.items():seen[p,slots[i]['day_idx']].append(slots[i]['name'])
        for (p,d),xs in seen.items():
            if len(xs)>1:rep.append({'role':role,'name':p,'day':DAYS[d],'slots':xs})
    lab=lambda i:f"{slots[i]['day']} {slots[i]['name']}节"
    return {'week':week,'week_type':'单周' if week%2 else '双周','free_table_sheet':sh,'free_table_title':title,'output':str(output),'extra_target':round(len(slots)*float(st.get('extra_slot_fraction',1/3))),'extra_actual':len(extra),'unfilled_minister':[lab(i) for i in mu],'unfilled_member':[lab(i) for i in bu],'minister_counts':dict(sorted(mc.items())),'member_counts':dict(sorted(bc.items())),'same_day_repeats':rep,'excluded_absent':True,'eight_am_extra_count':0,'cells_written':cells}

def main():
    here=Path(__file__).resolve().parent.parent;p=argparse.ArgumentParser();p.add_argument('--week',type=int,required=True);p.add_argument('--free-table',type=Path,required=True);p.add_argument('--template',type=Path,default=here/'assets/duty_roster_template.xlsx');p.add_argument('--config',type=Path,default=here/'config/roster.json');p.add_argument('--output',type=Path);p.add_argument('--report',type=Path);a=p.parse_args()
    if a.week<=0:p.error('--week must be positive')
    o=a.output or Path.cwd()/f'第{a.week}周_值班表.xlsx'
    if o.resolve() in {a.template.resolve(),a.free_table.resolve()}:p.error('output must be a new file')
    holder=None
    try:
        template,holder=resolve_template(a.template)
        r=generate(a.week,a.free_table,template,a.config,o)
    except (RosterError,XlsxError,zipfile.BadZipFile,ET.ParseError,KeyError,ValueError) as e:
        print(json.dumps({'ok':False,'error':str(e)},ensure_ascii=False,indent=2),file=sys.stderr);return 2
    finally:
        if holder is not None:holder.cleanup()
    if a.report:a.report.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'ok':True,**r},ensure_ascii=False,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
