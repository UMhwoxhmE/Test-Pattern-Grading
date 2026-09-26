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

def run_piece(pc, oc):
    global doc_page, shape
    page=pc['page']; doc_page=doc[page]
    if pc['mode']=='fixed':
        s=pc['size']; P,_=loop_for(page,s,pc['near']); G=P; tfun=lambda p: 0
        mark_size=lambda c: s
    else:
        G,_=blend(matched(page,pc['near']), pc['t'])
        mark_size=pc['mark']
    G=rdp(np.vstack([G,G[:1]]))
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
