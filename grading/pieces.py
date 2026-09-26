import numpy as np
from grade import smooth
D1=330.0   # below-dart blend zone above waist (pt): 20 -> 22
H=552.0    # waist to hip (side-seam hip notch) (pt): 22 -> 24
def upper(d): return 1-smooth(d/D1)          # d = distance above waist
def lower(d): return 1+smooth(d/H)           # d = distance below waist
def nearest_size(t): return ('20','22','24')[int(round(float(np.clip(t,0,2))))]
def up(dfun):  return dict(mode='grade', t=lambda p: upper(dfun(p)), mark=lambda c: nearest_size(upper(dfun(c))))
def lo(dfun):  return dict(mode='grade', t=lambda p: lower(dfun(p)), mark=lambda c: '24')
PIECES=[
 dict(name='Upper Front (p5)', page=4, near=(900,2350), **up(lambda p: 1588-p[0])),
 dict(name='Lower Front (p2)', page=1, near=(750,2700), **lo(lambda p: p[1]-2108)),
]
