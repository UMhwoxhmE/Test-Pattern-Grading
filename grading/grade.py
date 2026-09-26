import math, numpy as np
from outl import runs, out, pts_of

def loop_for(page, layer, near):
    """closed cutting-line loop for this size whose bbox centre is nearest `near` (x,y)"""
    best=None
    for r in runs(page, layer):
        if not r['closed'] or r['n']<3: continue
        b=r['bbox']; c=((b[0]+b[2])/2,(b[1]+b[3])/2)
        dd=math.dist(c,near)
        if best is None or dd<best[0]: best=(dd,r)
    P=np.array(best[1]['pts'])
    # drop closing duplicate / tiny steps
    keep=[P[0]]
    for q in P[1:]:
        if np.linalg.norm(q-keep[-1])>0.3: keep.append(q)
    P=np.array(keep)
    if np.linalg.norm(P[0]-P[-1])<0.3: P=P[:-1]
    # orient counter-clockwise in page coords (positive shoelace)
    a=0.5*np.sum(P[:,0]*np.roll(P[:,1],-1)-np.roll(P[:,0],-1)*P[:,1])
    if a<0: P=P[::-1]
    return P, best[1]

def resample_closed(P, step=1.0):
    Q=np.vstack([P,P[:1]])
    seg=np.linalg.norm(np.diff(Q,axis=0),axis=1); s=np.concatenate([[0],np.cumsum(seg)])
    n=int(s[-1]/step); t=np.linspace(0,s[-1],n,endpoint=False)
    return np.column_stack([np.interp(t,s,Q[:,0]),np.interp(t,s,Q[:,1])])

def corners(P, reach=6.0, thresh=30):
    R=resample_closed(P,1.0); n=len(R); k=int(reach)
    ang=np.zeros(n)
    for i in range(n):
        a=R[i]-R[(i-k)%n]; b=R[(i+k)%n]-R[i]
        c=np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)+1e-9)
        ang[i]=math.degrees(math.acos(max(-1,min(1,c))))
    C=[]
    for i in range(n):
        if ang[i]>thresh and all(ang[i]>=ang[(i+j)%n] for j in range(-k*2,k*2+1)):
            if not C or i-C[-1]>k*2: C.append(i)
    return R, C, ang

def strip_notches(P, maxbase=22, maxlen=70):
    """remove V notches cut into outline: path leaves and returns to (almost) same point"""
    R=resample_closed(P,1.0); n=len(R); keep=np.ones(n,bool); notches=[]
    i=0
    while i<n:
        found=False
        for L in range(12, maxlen):
            j=(i+L)%n
            if np.linalg.norm(R[j]-R[i])<min(maxbase, L/3.2):
                # depth: farthest point from chord
                idx=[(i+k)%n for k in range(L+1)]
                a,b=R[i],R[j]; ch=b-a; nrm=np.linalg.norm(ch)+1e-9
                dist=[abs(np.cross(ch,R[k]-a))/nrm if nrm>1 else np.linalg.norm(R[k]-a) for k in idx]
                kmax=idx[int(np.argmax(dist))]
                if max(dist)>6:
                    notches.append({'base':(a+b)/2,'apex':R[kmax].copy()})
                    for k in idx[1:-1]: keep[k]=False
                    i+=L; found=True; break
        if not found: i+=1
    return R[keep], notches

def smooth(u):
    u=np.clip(u,0,1); return u*u*(3-2*u)

def matched(page, near, sizes=('20','22','24')):
    """return per-size list of edges (arrays) with corresponding corners"""
    data={}
    for L in sizes:
        P,_=loop_for(page,L,near); R,C,_=corners(P); data[L]=(R,C)
    n=len(data[sizes[0]][1])
    assert all(len(data[L][1])==n for L in sizes), {L:len(data[L][1]) for L in sizes}
    ref=data[sizes[0]]; refc=[ref[0][i] for i in ref[1]]
    edges={}
    for L in sizes:
        R,C=data[L]; cc=[R[i] for i in C]
        # rotate corner list to best match reference
        best=min(range(n), key=lambda s: sum(np.linalg.norm(cc[(k+s)%n]-refc[k]) for k in range(n)))
        C=[C[(k+best)%n] for k in range(n)]
        err=max(np.linalg.norm(R[C[k]]-refc[k]) for k in range(n))
        assert err<120, (L,err)
        E=[]
        for k in range(n):
            a,b=C[k],C[(k+1)%n]
            idx=list(range(a,b+1)) if b>a else list(range(a,len(R)))+list(range(0,b+1))
            E.append(R[idx])
        edges[L]=E
    return edges

def resample_open(P, m):
    seg=np.linalg.norm(np.diff(P,axis=0),axis=1); s=np.concatenate([[0],np.cumsum(seg)])
    t=np.linspace(0,s[-1],m)
    return np.column_stack([np.interp(t,s,P[:,0]),np.interp(t,s,P[:,1])])

def blend(edges, tfun, sizes=('20','22','24')):
    """tfun(point)-> t in [0,2]; 0=sizes[0],1=sizes[1],2=sizes[2]. returns closed polyline + per-point t"""
    out=[]; ts=[]
    for k in range(len(edges[sizes[0]])):
        m=max(len(edges[L][k]) for L in sizes)+1
        A,B,Cc=[resample_open(edges[L][k],m) for L in sizes]
        t=np.array([tfun(p) for p in B])
        w0=np.clip(1-t,0,1); w2=np.clip(t-1,0,1); w1=1-w0-w2
        G=A*w0[:,None]+B*w1[:,None]+Cc*w2[:,None]
        out.append(G[:-1]); ts.append(t[:-1])
    return np.vstack(out), np.concatenate(ts)
