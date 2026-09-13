from collections import defaultdict,deque
import hashlib,math,re

DAYS=['星期一','星期二','星期三','星期四','星期五']; FC=['D','E','F','G','H']; TC=['B','C','D','E','F']
SLOTS=[('1-2',(3,4),3),('3-4',(5,6),4),('5-6',(7,8),5),('7-8',(9,10),6),('9-10',None,7)]

def names(text,week):
    text=(text or '').replace(' ','').replace('\n',''); out=set()
    for item in re.split('、',text):
        m=re.fullmatch(r'([^（）()]+?)(?:[（(]([^）)]+)[）)])?',item)
        if not m: continue
        n,e=m.group(1),m.group(2)
        if not e: out.add(n); continue
        ok=False
        for x in re.split(r'[，,、;；]+',e.replace('—','~').replace('-','~')):
            q=re.fullmatch(r'(\d+)~(\d+)',x)
            if q and int(q.group(1))<=week<=int(q.group(2)):ok=True
            elif x.isdigit() and int(x)==week:ok=True
        if ok:out.add(n)
    return out

def availability(vals,week,people,settings):
    slots=[]; av=[]
    for d,day in enumerate(DAYS):
        for k,(sn,rows,tr) in enumerate(SLOTS):
            slots.append({'day_idx':d,'day':day,'name':sn,'row':tr})
            if sn=='9-10' and settings.get('evening_is_default_free',True): a=set(people)
            elif d==1 and sn in {'5-6','7-8'} and settings.get('tuesday_afternoon_public_break',True): a=set(people)
            else:
                r1,r2=rows; a=names(vals.get(f'{FC[d]}{r1}',''),week)&names(vals.get(f'{FC[d]}{r2}',''),week)
            av.append(a)
    return slots,av

def tie(name,week,s): return int(hashlib.sha1(f'{week}|{s}|{name}'.encode()).hexdigest()[:8],16)
class E:
    def __init__(self,to,rev,cap,cost,meta=None):self.to=to;self.rev=rev;self.cap=cap;self.orig=cap;self.cost=cost;self.meta=meta
class MCF:
    def __init__(self,n):self.g=[[] for _ in range(n)]
    def add(self,a,b,cap,cost,meta=None):
        x=E(b,len(self.g[b]),cap,cost,meta); y=E(a,len(self.g[a]),0,-cost); self.g[a].append(x);self.g[b].append(y)
    def flow(self,s,t,lim):
        f=0
        while f<lim:
            n=len(self.g);dist=[10**9]*n;pv=[-1]*n;pe=[-1]*n;inq=[0]*n;dist[s]=0;q=deque([s])
            while q:
                v=q.popleft();inq[v]=0
                for i,e in enumerate(self.g[v]):
                    if e.cap and dist[v]+e.cost<dist[e.to]:
                        dist[e.to]=dist[v]+e.cost;pv[e.to]=v;pe[e.to]=i
                        if not inq[e.to]:q.append(e.to);inq[e.to]=1
            if dist[t]>=10**9:break
            v=t
            while v!=s:self.g[pv[v]][pe[v]].cap-=1;self.g[v][self.g[pv[v]][pe[v]].rev].cap+=1;v=pv[v]
            f+=1
        return f

def assign(slots,av,people,week,target,cap,avoid=True):
    ps=set(people); fill=[i for i in range(len(slots)) if av[i]&ps]
    def run(mx,daycap):
        N=1;sn={i:N+j for j,i in enumerate(fill)};N+=len(fill);pn={};pd={}
        for p in people:
            pn[p]=N;N+=1
            for d in range(5):pd[p,d]=N;N+=1
        sink=N;m=MCF(sink+1)
        for i in fill:
            m.add(0,sn[i],1,0);d=slots[i]['day_idx']
            for p in sorted(av[i]&ps,key=lambda x:tie(x,week,f's{i}')):m.add(sn[i],pd[p,d],1,tie(p,week,f'e{i}')%7,(i,p))
        for p in people:
            for d in range(5):m.add(pd[p,d],pn[p],daycap,0)
            for k in range(1,mx+1):m.add(pn[p],sink,1,(k-1)*3 if k<=target else 30+40*(k-target-1)+tie(p,week,f'p{k}')%5)
        got=m.flow(0,sink,len(fill));a={}
        for i in fill:
            for e in m.g[sn[i]]:
                if e.meta and e.orig==1 and e.cap==0:a[i]=e.meta[1];break
        return got,a
    for dc in ([1,2] if avoid else [2]):
        for mx in range(cap,cap+4):
            got,a=run(mx,dc)
            if got==len(fill):return a,[i for i in range(len(slots)) if i not in a]
    got,a=run(cap+5,5);return a,[i for i in range(len(slots)) if i not in a]

def extras(slots,av,members,base,mins,week,target):
    ms=set(members); eligible=[i for i,s in enumerate(slots) if s['name']!='1-2' and i in base and i in mins and ((av[i]&ms)-{base[i]})]
    used=defaultdict(int);counts=defaultdict(int)
    for i,p in base.items():used[p,slots[i]['day_idx']]+=1;counts[p]+=1
    def run(mx,relax):
        N=1;sn={i:N+j for j,i in enumerate(eligible)};N+=len(eligible);pn={};pd={}
        for p in members:
            pn[p]=N;N+=1
            for d in range(5):pd[p,d]=N;N+=1
        sink=N;m=MCF(sink+1)
        for i in eligible:
            m.add(0,sn[i],1,0);d=slots[i]['day_idx']
            for p in sorted((av[i]&ms)-{base[i]},key=lambda x:tie(x,week,f'x{i}')):
                if not relax and used[p,d]:continue
                m.add(sn[i],pd[p,d],1,tie(p,week,f'xe{i}')%9,(i,p))
        for p in members:
            for d in range(5):
                if relax or not used[p,d]:m.add(pd[p,d],pn[p],1,0)
            for total in range(counts[p]+1,mx+1):m.add(pn[p],sink,1,8*max(0,total-1)+60*max(0,total-2)+tie(p,week,f'xp{total}')%5)
        m.flow(0,sink,min(target,len(eligible)));a={}
        for i in eligible:
            for e in m.g[sn[i]]:
                if e.meta and e.orig==1 and e.cap==0:a[i]=e.meta[1];break
        return a
    for mx,relax in [(2,0),(3,0),(3,1)]:
        a=run(mx,relax)
        if len(a)>=min(target,len(eligible)):return a
    return run(4,1)
