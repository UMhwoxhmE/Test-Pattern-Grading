import numpy as np
from grade import smooth, resample_closed
D1=330.0   # blend zone above waist (pt): 20 -> 22. Starts just below the side dart / back side-seam notch.
H=552.0    # waist to hip (pt): 22 -> 24. Matches the side-seam hip notch on all lower pieces.
def upper(d): return 1-smooth(d/D1)          # d = distance above waist
def lower(d): return 1+smooth(d/H)           # d = distance below waist
def nearest_size(t): return ('20','22','24')[int(round(float(np.clip(t,0,2))))]
def up(dfun):  return dict(mode='grade', t=lambda p: upper(dfun(p)), mark=lambda c: nearest_size(upper(dfun(c))))
def lo(dfun):  return dict(mode='grade', t=lambda p: lower(dfun(p)), mark=lambda c: '24')
def fixed(size, **kw): return dict(mode='fixed', size=size, **kw)

# Zipper facing: E/F cup "cut here" curve from the Labels layer (page 3)
EF_CURVE=np.array([(272.0,3230.7),(212.6,3230.7),(194.4,3229.7),(185.0,3228.4),(166.4,3223.6),(160.0,3221.1),
                   (145.6,3213.1),(135.8,3204.3),(131.8,3198.5),(128.0,3188.9),(126.0,3173.5),(125.9,3160.5)])
def ef_cut(P):
    R=resample_closed(P,1.0)
    keep=R[:,1]<3160.0
    # rotate so the removed chunk is at the end
    i=int(np.argmax(~keep)); R=np.roll(R,-i,axis=0); keep=np.roll(keep,-i)
    j=int(np.argmax(keep)); body=R[j:][keep[j:]]
    curve=EF_CURVE if np.linalg.norm(body[-1]-EF_CURVE[0])<np.linalg.norm(body[-1]-EF_CURVE[-1]) else EF_CURVE[::-1]
    return np.vstack([body,curve])

PIECES=[
 # ---- graded 20 (bust) -> 22 (waist) -> 24 (hip)
 dict(name='Upper Front (p5)',        page=4, near=(900,2350),  **up(lambda p: 1588-p[0])),
 dict(name='Upper Front Lining (p5)', page=4, near=(970,1050),  **up(lambda p: 1719-p[1])),
 dict(name='Upper Back (p1)',         page=0, near=(600,1385),  **up(lambda p: 2077-p[1])),
 dict(name='Upper Back Lining (p3)',  page=2, near=(1680,820),  **up(lambda p: p[1]-150.5)),
 dict(name='Lower Front (p2)',        page=1, near=(750,2700),  **lo(lambda p: p[1]-2108)),
 dict(name='Lower Front Lining (p3)', page=2, near=(820,1590),  **lo(lambda p: 1323-p[0])),
 dict(name='Lower Back (p2)',         page=1, near=(770,1000),  **lo(lambda p: p[0]-97)),
 dict(name='Lower Back Lining (p3)',  page=2, near=(1700,2660), **lo(lambda p: 3261-p[1])),
 # ---- bust size 20: sleeves, hood, collar/neck pieces, CF pieces
 dict(name='Back Neckline Facing (p1)', page=0, near=(685,285),   **fixed('20')),
 dict(name='Hood Inset (p1)',           page=0, near=(2007,966),  **fixed('20')),
 dict(name='Hood Facing (p1)',          page=0, near=(1248,2727), **fixed('20')),
 dict(name='Hood (p1)',                 page=0, near=(615,2726),  **fixed('20')),
 dict(name='Cuff (p2)',                 page=1, near=(1812,2858), **fixed('20')),
 dict(name='Hood Inset Lining (p2)',    page=1, near=(1194,1881), **fixed('20')),
 dict(name='Hood Lining (p2)',          page=1, near=(1769,649),  **fixed('20')),
 dict(name='Sleeve Interfacing (p2)',   page=1, near=(2165,1767), **fixed('20')),
 dict(name='Brim (p3)',                 page=2, near=(504,630),   **fixed('20')),
 dict(name='Zipper Facing E/F (p3)',    page=2, near=(200,2115),  **fixed('20', post=ef_cut)),
 dict(name='Front Neckline Facing (p5)',page=4, near=(1611,1477), **fixed('20')),
 dict(name='Zipper Flap (p5)',          page=4, near=(2103,1898), **fixed('20')),
 dict(name='Sleeve Full Bicep (p9)',    page=8, near=(1208,1349), **fixed('20')),
 dict(name='Sleeve Lining Full Bicep (p10)', page=9, near=(1242,1186), **fixed('20')),
 # ---- hip size 24: pockets and hem facings (pieces identical in all sizes marked *)
 dict(name='Pocket Flap* (p1)',         page=0, near=(1354,324),  **fixed('24')),
 dict(name='Pocket* (p1)',              page=0, near=(1373,976),  notches=[(1058,764.5),(1689,764.5)], **fixed('24')),  # fold line notches
 dict(name='Back Hem Facing (p1)',      page=0, near=(2071,2718), **fixed('24')),
 dict(name='Front Hem Facing (p1)',     page=0, near=(1649,2520), **fixed('24')),
 dict(name='Pocket Interfacing* (p3)',  page=2, near=(464,261),   **fixed('24')),
 dict(name='Back Vent Interfacing* (p3)',page=2, near=(550,2694), **fixed('24')),
]
