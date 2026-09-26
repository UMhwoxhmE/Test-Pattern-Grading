import pymupdf as fitz, numpy as np, math
from matplotlib.path import Path
from grade import matched, blend, smooth, loop_for
from outl import runs, out

from outl import SRC
import os
DST=os.environ.get("GRADED_PDF","graded.pdf")
COLOR=(0.85,0.0,0.55); WIDTH=2.2
SIZES=('20','22','24')

def rdp(P, eps=0.25):
    if len(P)<3: return P
    a,b=P[0],P[-1]; ab=b-a; n=np.linalg.norm(ab)
    d=np.abs(np.cross(ab,P-a))/n if n>1e-9 else np.linalg.norm(P-a,axis=1)
    i=int(np.argmax(d))
    if d[i]>eps: return np.vstack([rdp(P[:i+1],eps)[:-1], rdp(P[i:],eps)])
    return np.array([a,b])

def markings(page, size, outline):
    """drawings (original objects) of this size inside the piece outline, excluding the outline itself"""
    path=Path(outline); res=[]
    for r in runs(page,size):
        if r['closed'] and r['n']>5: continue       # an outline
        pts=np.array(r['pts'])
        if path.contains_points(pts, radius=-8).mean()>0.5 or path.contains_point(pts.mean(0)):
            res.append(r)
    return res

def run_items(page, r, layer):
    """original drawings making up a marking run -> list of (items, dashes, type, closePath)"""
    res=[]
    for x in out[page]:
        if x['layer']==layer and r['first']<=x['seqno']<=r['last'] and x['type']=='s':
            its=[it for it in x['items'] if it[0] in 'lc']
            if its: res.append((its, x['dashes'], 's', False))
    return res

LABEL_SKIP={(2,3084),(2,3085)}   # C/D and E/F cup cut lines on zipper facing (E/F is the cutting line itself)

def add_notch(G, pt, depth=14.0, half=8.0):
    """cut a V notch into closed polyline G at the point of G nearest pt"""
    pt=np.asarray(pt,float); n=len(G); best=None
    for i in range(n):
        a,b=G[i],G[(i+1)%n]; ab=b-a; u=np.clip(np.dot(pt-a,ab)/max(np.dot(ab,ab),1e-9),0,1)
        q=a+u*ab; dd=np.linalg.norm(pt-q)
        if best is None or dd<best[0]: best=(dd,i,q,ab/np.linalg.norm(ab))
    _,i,q,t=best; nrm=np.array([-t[1],t[0]])
    if not Path(G).contains_point(q+nrm*3): nrm=-nrm
    V=np.array([q-half*t, q+depth*nrm, q+half*t])
    return np.vstack([G[:i+1],V,G[i+1:]])

def label_items(page, G):
    """fold/placement/trim lines and grainlines from the Labels layer that belong to this piece"""
    path=Path(G); res=[]
    for x in out[page]:
        if x['layer']!='Labels' or (page,x['seqno']) in LABEL_SKIP: continue
        if any(it[0] in ('qu','re') for it in x['items']): continue      # label boxes
        r=x['rect']; c=((r.x0+r.x1)/2,(r.y0+r.y1)/2)
        if not (path.contains_point(c) or path.contains_point(c,radius=4) or path.contains_point(c,radius=-4)): continue
        its=[it for it in x['items'] if it[0] in 'lc']
        if its: res.append((its, x.get('dashes'), x['type'], bool(x.get('closePath')), x['seqno']))
    return res

def piece_markings(pc, G, mark_size):
    """markings for a piece: size-layer markings (dart, dots, placement, lengthen) + Labels lines"""
    page=pc['page']; res=[]
    for s in (SIZES if pc['mode']!='fixed' else (pc['size'],)):
        own=loop_for(page,s,pc['near'])[0]
        for r in markings(page,s,own):
            if mark_size(np.array(r['pts']).mean(0))==s:
                res+= [(i,d,t,c,None) for i,d,t,c in run_items(page,r,s)]
    return res + label_items(page,G)

def piece_outline(pc):
    """final graded cutting line (closed polyline, page coords) and marking-size chooser"""
    page=pc['page']
    if pc['mode']=='fixed':
        s=pc['size']; P,_=loop_for(page,s,pc['near']); G=P
        if 'post' in pc: G=pc['post'](G)
        mark_size=lambda c: s
    else:
        G,_=blend(matched(page,pc['near']), pc['t'])
        mark_size=pc['mark']
    G=rdp(np.vstack([G,G[:1]]))[:-1]
    for np_ in pc.get('notches',[]): G=add_notch(G,np_)
    return G, mark_size

def run_piece(pc, oc):
    page=pc['page']; shape=doc[page].new_shape()
    G, mark_size = piece_outline(pc)
    shape.draw_polyline([fitz.Point(*p) for p in G]); shape.finish(color=COLOR, width=WIDTH, closePath=True, lineJoin=1, oc=oc)
    M=piece_markings(pc, G, mark_size)
    for its,dash,typ,closed,_ in M:
        for it in its:
            if it[0]=='l': shape.draw_line(it[1],it[2])
            else: shape.draw_bezier(*it[1:5])
        fill=COLOR if typ in ('f','fs') else None
        stroke=COLOR if typ in ('s','fs') else None
        dash=None if dash in ('[] 0',None) else dash
        shape.finish(color=stroke, fill=fill, width=WIDTH*0.6, dashes=dash, closePath=closed or fill is not None, oc=oc)
    shape.commit()
    return G, len(M)

if __name__=="__main__":
    from pieces import PIECES
    doc=fitz.open(SRC)
    oc=doc.add_ocg("Graded 20-22-24", on=True)
    for pc in PIECES:
        G,n=run_piece(pc, oc)
        print(pc['name'], len(G), "pts,", n, "marking runs")
    doc.save(DST, garbage=3, deflate=True)
