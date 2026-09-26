import math, os
import pymupdf as fitz
# Source pattern PDF (Cashmerette Marston A0 file). Not committed: supply your own copy.
SRC=os.environ.get("PATTERN_PDF","pattern.pdf")
_doc=fitz.open(SRC)
PAGES=[0,1,2,4,8,9]   # pattern pages 1-3, 5 (E/F cup), 9-10 (full bicep)
out={i:[x for x in _doc[i].get_drawings() if x.get('layer') in ('18','20','22','24','26','Labels')] for i in PAGES}
def pts_of(x):
    P=[]
    for it in x['items']:
        if it[0]=='l': seg=[it[1],it[2]]
        elif it[0]=='c': seg=[it[1],it[2],it[3],it[4]]; 
        else: continue
        if it[0]=='c':
            a,b,c,d=seg; seg=[ (a*(1-t)**3+b*3*t*(1-t)**2+c*3*t*t*(1-t)+d*t**3) for t in [i/8 for i in range(9)]]
        for q in seg:
            q=(q.x,q.y)
            if not P or math.dist(P[-1],q)>1e-6: P.append(q)
    return P
def runs(page, layer, gap=70):
    xs=sorted([x for x in out[page] if x['layer']==layer and x['type']=='s'], key=lambda x:x['seqno'])
    R=[]; cur=None
    for x in xs:
        P=pts_of(x)
        if not P: continue
        if cur and math.dist(cur['pts'][-1],P[0])<gap and x['seqno']-cur['last']<=3:
            cur['pts']+=P; cur['last']=x['seqno']; cur['n']+=1
        else:
            cur={'pts':list(P),'first':x['seqno'],'last':x['seqno'],'n':1}; R.append(cur)
    for r in R:
        r['closed']=math.dist(r['pts'][0],r['pts'][-1])<gap
        xs_=[p[0] for p in r['pts']]; ys=[p[1] for p in r['pts']]
        r['bbox']=(min(xs_),min(ys),max(xs_),max(ys))
    return R
if __name__=="__main__":
    import sys
    for L in ('20','22','24'):
        for r in runs(int(sys.argv[1]),L):
            if r['n']>1 or r['closed']: print(L, r['first'],r['last'],r['n'],r['closed'],[round(v) for v in r['bbox']], round(math.dist(r['pts'][0],r['pts'][-1])))
