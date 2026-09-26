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

def draw_run(page, r, layer, oc, shift=(0,0)):
    dx,dy=shift
    for x in out[page]:
        if x['layer']==layer and r['first']<=x['seqno']<=r['last'] and x['type']=='s':
            for it in x['items']:
                if it[0]=='l': pts=[it[1],it[2]]
                elif it[0]=='c': pts=None
                else: continue
                dash=None if x['dashes'] in ('[] 0',None) else x['dashes']
                if it[0]=='l':
                    shape.draw_line(fitz.Point(pts[0].x+dx,pts[0].y+dy),fitz.Point(pts[1].x+dx,pts[1].y+dy))
                else:
                    a,b,c,d=it[1:5]
                    shape.draw_bezier(a,b,c,d)
                shape.finish(color=COLOR,width=WIDTH*0.6,dashes=dash,closePath=False,oc=oc)

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

def copy_labels(page, G, oc):
    """fold/placement/trim lines and grainlines from the Labels layer that belong to this piece"""
    path=Path(G); n=0
    for x in out[page]:
        if x['layer']!='Labels' or (page,x['seqno']) in LABEL_SKIP: continue
        if any(it[0] in ('qu','re') for it in x['items']): continue      # label boxes
        r=x['rect']; c=((r.x0+r.x1)/2,(r.y0+r.y1)/2)
        if not (path.contains_point(c) or path.contains_point(c,radius=4) or path.contains_point(c,radius=-4)): continue
        for it in x['items']:
            if it[0]=='l': shape.draw_line(it[1],it[2])
            elif it[0]=='c': shape.draw_bezier(*it[1:5])
        fill=COLOR if x['type'] in ('f','fs') else None
        stroke=COLOR if x['type'] in ('s','fs') else None
        dash=None if x.get('dashes') in ('[] 0',None) else x['dashes']
        shape.finish(color=stroke, fill=fill, width=WIDTH*0.6, dashes=dash, closePath=bool(x.get('closePath')) or fill is not None, oc=oc)
        n+=1
    return n

def run_piece(pc, oc):
    global doc_page, shape
    page=pc['page']; doc_page=doc[page]
    if pc['mode']=='fixed':
        s=pc['size']; P,_=loop_for(page,s,pc['near']); G=P
        if 'post' in pc: G=pc['post'](G)
        mark_size=lambda c: s
    else:
        G,_=blend(matched(page,pc['near']), pc['t'])
        mark_size=pc['mark']
    G=rdp(np.vstack([G,G[:1]]))[:-1]
    for np_ in pc.get('notches',[]): G=add_notch(G,np_)
    shape=doc_page.new_shape()
    shape.draw_polyline([fitz.Point(*p) for p in G]); shape.finish(color=COLOR, width=WIDTH, closePath=True, lineJoin=1, oc=oc)
    # markings: from the size chosen at each marking's location
    base=loop_for(page,'24' if pc['mode']!='fixed' else pc['size'],pc['near'])[0]
    seen=0
    for s in (SIZES if pc['mode']!='fixed' else (pc['size'],)):
        own=loop_for(page,s,pc['near'])[0]
        for r in markings(page,s,own):
            c=np.array(r['pts']).mean(0)
            if mark_size(c)==s:
                draw_run(page,r,s,oc); seen+=1
    seen+=copy_labels(page,G,oc)
    shape.commit()
    return G, seen

if __name__=="__main__":
    from pieces import PIECES
    doc=fitz.open(SRC)
    oc=doc.add_ocg("Graded 20-22-24", on=True)
    for pc in PIECES:
        G,n=run_piece(pc, oc)
        print(pc['name'], len(G), "pts,", n, "marking runs")
    doc.save(DST, garbage=3, deflate=True)
