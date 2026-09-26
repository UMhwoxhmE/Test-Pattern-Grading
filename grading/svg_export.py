"""Export the graded pieces as an Inkscape SVG for nesting.

Each piece outline is a path labelled "<num> <Name> <cut codes>" (e.g. "1 Upper Front C2M"),
with its grainline as a separate path labelled/id'd "grain-<num>". For cut-on-fold pieces the
grain path lies exactly on the fold edge. Units are mm.
"""
import os, re, numpy as np
import pymupdf as fitz
from matplotlib.path import Path
from build import piece_outline, piece_markings
from outl import SRC
from pieces import PIECES

PT2MM = 25.4/72
GAP_MM = 50.0
MATERIAL = {'main': 'M', 'lining': 'L', 'interfacing': 'I', 'ribbing': 'R'}


def piece_text(page_lines, G):
    path = Path(G)
    return [(bb, t, sz) for bb, t, sz in page_lines
            if path.contains_point(((bb[0]+bb[2])/2, (bb[1]+bb[3])/2))]


def piece_info(lines):
    """number, name, cut codes from the pattern's label text"""
    NUM = re.compile(r'^(INT ?\d+|\d+[A-Z]?)$')
    big = [(bb, t) for bb, t, sz in lines if sz > 20 and NUM.match(t)]
    nb, num = big[0]; num = num.replace(' ', '')
    if not num.startswith('INT'):
        num = re.match(r'\d+', num).group(0)              # 1B -> 1 (cup/bicep variant)
    # piece name: upper-case line in the label box (same font size as the cut text), nearest the number
    cut_sz = next(sz for _, t, sz in lines if t.startswith('Cut '))
    skip = ('CUP', 'BICEP', 'OPTIONAL', 'CUT HERE')
    names = [(bb, t) for bb, t, sz in lines if t.isupper() and abs(sz-cut_sz) < 0.5 and not any(k in t for k in skip)]
    name = min(names, key=lambda n: np.hypot((n[0][0]+n[0][2])/2-(nb[0]+nb[2])/2, (n[0][1]+n[0][3])/2-(nb[1]+nb[3])/2))[1]
    # cut instructions: "Cut 2 main fabric", "& 1 interfacing", "Cut on fold: Cut 1 main" + "fabric & ..."
    cut = ' '.join(t for _, t, sz in lines if abs(sz-cut_sz) < 0.5 and t.startswith(('Cut ', '& ', 'fabric')))
    on_fold = 'on fold' in cut.lower()
    codes = []
    for n, mat in re.findall(r'(\d+)\s+(main|lining|interfacing|ribbing)', cut.lower()):
        codes.append(f"C{n}{MATERIAL[mat]}" + ("OF" if on_fold else ""))
    return num, name.title(), codes, on_fold


def near(p, fills, tol=25):
    return any(np.linalg.norm(np.asarray(p)-c) < tol for c in fills)


def grain_line(M, G, on_fold):
    fills = [np.mean([[it[1].x, it[1].y] for it in its], axis=0) for its, _, typ, _, _ in M if typ == 'f']
    strokes = [(its, sq) for its, _, typ, _, sq in M if typ == 's']
    if not on_fold:
        cands = []
        for its, sq in strokes:
            if len(its) == 1 and its[0][0] == 'l':
                a, b = (its[0][1].x, its[0][1].y), (its[0][2].x, its[0][2].y)
                if near(a, fills) and near(b, fills):
                    cands.append((np.hypot(b[0]-a[0], b[1]-a[1]), a, b, sq))
        L, a, b, sq = max(cands)
        return np.array([a, b]), {sq}
    # fold: bracket = multi-segment stroke whose ends carry arrowheads; grain = outline edge it points at
    for its, sq in strokes:
        if len(its) >= 2:
            pts = [(its[0][1].x, its[0][1].y), (its[-1][2].x, its[-1][2].y)]
            if near(pts[0], fills) and near(pts[1], fills):
                tips = np.array(pts)
                break
    n = len(G); best = None
    for i in range(n):
        a, b = G[i], G[(i+1) % n]; ab = b-a; L = np.linalg.norm(ab)
        if L < 100: continue
        t = ab/L; nrm = np.array([-t[1], t[0]])
        d = np.mean([abs(np.dot(q-a, nrm)) for q in tips])
        if best is None or d < best[0]: best = (d, a, b)
    arrow_fills = {sq for its, _, typ, _, sq in M if typ == 'f'}
    return np.array([best[1], best[2]]), {sq}


def d_poly(P, closed, off):
    P = (np.asarray(P)*PT2MM) + off
    s = "M " + " L ".join(f"{x:.3f},{y:.3f}" for x, y in P)
    return s + (" Z" if closed else "")


def d_items(its, off):
    out = []; cur = None
    for it in its:
        pts = [((p.x*PT2MM)+off[0], (p.y*PT2MM)+off[1]) for p in it[1:(3 if it[0] == 'l' else 5)]]
        if cur is None or np.hypot(pts[0][0]-cur[0], pts[0][1]-cur[1]) > 1e-3:
            out.append(f"M {pts[0][0]:.3f},{pts[0][1]:.3f}")
        if it[0] == 'l': out.append(f"L {pts[1][0]:.3f},{pts[1][1]:.3f}")
        else: out.append("C " + " ".join(f"{x:.3f},{y:.3f}" for x, y in pts[1:]))
        cur = pts[-1]
    return " ".join(out)


def export(dst, with_markings=False):
    doc = fitz.open(SRC)
    pages = sorted({pc['page'] for pc in PIECES})
    pw = doc[0].rect.width*PT2MM; ph = doc[0].rect.height*PT2MM
    offs = {pg: np.array([k*(pw+GAP_MM), 0.0]) for k, pg in enumerate(pages)}
    W = len(pages)*(pw+GAP_MM) - GAP_MM
    lines = {}
    for pg in pages:
        lines[pg] = [(l['bbox'], "".join(s['text'] for s in l['spans']).strip(), l['spans'][0]['size'])
                     for b in doc[pg].get_text("dict")["blocks"] for l in b.get("lines", [])]
    pieces_svg, grains_svg, marks_svg, names = [], [], [], []
    for pc in PIECES:
        G, mark_size = piece_outline(pc)
        M = piece_markings(pc, G, mark_size)
        num, name, codes, on_fold = piece_info(piece_text(lines[pc['page']], G))
        label = f"{num} {name} {' '.join(codes)}"
        pid = "piece-" + re.sub(r'[^A-Za-z0-9]+', '_', label).strip('_')
        gline, used = grain_line(M, G, on_fold)
        off = offs[pc['page']]
        names.append((label, f"grain-{num}"))
        pieces_svg.append(f'    <path id="{pid}" inkscape:label="{label}" d="{d_poly(G, True, off)}" '
                          f'style="fill:none;stroke:#000000;stroke-width:0.5"/>')
        grains_svg.append(f'    <path id="grain-{num}" inkscape:label="grain-{num}" d="{d_poly(gline, False, off)}" '
                          f'style="fill:none;stroke:#d4008c;stroke-width:0.5"/>')
        if with_markings:
            # everything except the grainline / fold bracket and its arrowheads
            fills = [np.mean([[it[1].x, it[1].y] for it in its], axis=0) for its, _, typ, _, _ in M if typ == 'f']
            gpts = [np.array([gline[0]]), np.array([gline[1]])]
            parts = []
            for its, dash, typ, closed, sq in M:
                if sq in used: continue
                if typ == 'f': continue            # arrowheads (grainline / fold bracket)
                if sq is not None:
                    # skip Labels fold brackets (their grain is the fold edge)
                    ends = [(its[0][1].x, its[0][1].y), (its[-1][-1].x, its[-1][-1].y)]
                    if len(its) >= 2 and near(ends[0], fills) and near(ends[1], fills): continue
                da = '' if dash in (None, '[] 0') else ';stroke-dasharray:' + ','.join(
                    f"{float(v)*PT2MM:.2f}" for v in re.findall(r'[\d.]+', dash.split(']')[0]))
                parts.append(f'      <path d="{d_items(its, off)}{" Z" if closed else ""}" '
                             f'style="fill:none;stroke:#000000;stroke-width:0.3{da}"/>')
            marks_svg.append(f'    <g id="marks-{num}" inkscape:label="marks-{num}">\n' + "\n".join(parts) + '\n    </g>')
    svg = [f'<?xml version="1.0" encoding="UTF-8"?>',
           f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
           f'width="{W:.1f}mm" height="{ph:.1f}mm" viewBox="0 0 {W:.3f} {ph:.3f}">',
           '  <g id="layer-pieces" inkscape:groupmode="layer" inkscape:label="Pieces">', *pieces_svg, '  </g>',
           '  <g id="layer-grain" inkscape:groupmode="layer" inkscape:label="Grainlines">', *grains_svg, '  </g>']
    if with_markings:
        svg += ['  <g id="layer-markings" inkscape:groupmode="layer" inkscape:label="Markings">', *marks_svg, '  </g>']
    svg.append('</svg>')
    open(dst, 'w').write("\n".join(svg) + "\n")
    return names


if __name__ == "__main__":
    base = os.environ.get("SVG_OUT", "Marston_Raincoat_graded_20-22-24")
    names = export(base + ".svg")
    export(base + "_with_markings.svg", with_markings=True)
    for n in names: print(n)
